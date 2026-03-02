"""
RAG용 certificates_vectors 테이블을 DB의 qualification 데이터로 채웁니다.
- Recursive Chunking (chunk 1000, overlap 150) + [자격증명: {name}] 태깅
- content_hash(SHA-256)로 변경분만 임베딩 호출 (중복 제거)

실행: cert-app/backend 에서 (openai 패키지 필요)
  uv run python scripts/populate_certificates_vectors.py
  또는: 가상환경 활성화 후 python scripts/populate_certificates_vectors.py

옵션:
  --truncate   기존 certificates_vectors 전체 삭제 후 채우기 (기본: 기존 qual_id 행만 갱신)
  --batch N    임베딩 API 배치 크기 (기본 50)
  --dry-run    DB 쓰기 없이 content/청크 건수만 출력

사전: migrations/rag_hybrid_content_hash_hnsw.sql 적용 필요 (content_hash, chunk_index, content_tsv).
"""
import argparse
import hashlib
import json
import logging
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from app.database import SessionLocal
from app.config import get_settings

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)
settings = get_settings()

# Chunk 설정 (문맥 보존)
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 150
CONTEXT_TAG_PREFIX = "[자격증명: "


def build_content(row: dict) -> str:
    """자격 한 건을 RAG 검색에 유리한 한 문단 텍스트로 만듦."""
    parts = [
        str(row.get("qual_name") or "").strip(),
        str(row.get("qual_type") or "").strip(),
        str(row.get("main_field") or "").strip(),
        str(row.get("ncs_large") or "").strip(),
        str(row.get("managing_body") or "").strip(),
        str(row.get("grade_code") or "").strip(),
    ]
    return " ".join(p for p in parts if p).replace("\n", " ").strip() or "자격증"


def content_hash(text_content: str) -> str:
    """SHA-256 해시. 변경 시에만 임베딩 호출용."""
    return hashlib.sha256(text_content.encode("utf-8")).hexdigest()


def chunk_with_tag(full_content: str, qual_name: str) -> list[str]:
    """
    Recursive chunking (문단 → 문장 → 마침표 순) + 각 청크 앞에 [자격증명: {name}] 태그.
    """
    from langchain_text_splitters import RecursiveCharacterTextSplitter

    tag = f"{CONTEXT_TAG_PREFIX}{qual_name}] "
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " "],
        length_function=len,
    )
    raw_chunks = splitter.split_text(full_content.strip() or "자격증")
    return [tag + c.strip() if not c.strip().startswith(CONTEXT_TAG_PREFIX) else c.strip() for c in raw_chunks]


def get_embeddings_batch(texts: list[str], model: str = "text-embedding-3-small") -> list[list[float]]:
    """OpenAI Embedding API 배치 호출 (한 번에 여러 텍스트)."""
    if not texts:
        return []
    from openai import OpenAI
    client = OpenAI(api_key=settings.OPENAI_API_KEY)
    texts = [t.replace("\n", " ").strip() or " " for t in texts]
    resp = client.embeddings.create(input=texts, model=model)
    return [d.embedding for d in resp.data]


def main():
    parser = argparse.ArgumentParser(description="Populate certificates_vectors from qualification table (chunked + hash)")
    parser.add_argument("--truncate", action="store_true", help="TRUNCATE certificates_vectors before insert")
    parser.add_argument("--batch", type=int, default=50, help="Embedding batch size (default 50)")
    parser.add_argument("--dry-run", action="store_true", help="No DB write, only print counts and sample content")
    args = parser.parse_args()

    try:
        from openai import OpenAI  # noqa: F401
    except ImportError:
        logger.error(
            "패키지 'openai'가 없습니다. cert-app/backend에서 다음 중 하나로 실행하세요:\n"
            "  uv run python scripts/populate_certificates_vectors.py\n"
            "  또는: pip install openai 후 동일 명령"
        )
        sys.exit(1)

    if not settings.OPENAI_API_KEY:
        logger.error("OPENAI_API_KEY not set. Set it in .env")
        sys.exit(1)

    db = SessionLocal()
    try:
        rows = db.execute(
            text("""
                SELECT qual_id, qual_name, qual_type, main_field, ncs_large, managing_body, grade_code
                FROM qualification
                WHERE is_active = TRUE
                ORDER BY qual_id
            """)
        ).fetchall()
        rows = [r._mapping for r in rows] if hasattr(rows[0], "_mapping") else [dict(r) for r in rows]
    finally:
        db.close()

    if not rows:
        logger.warning("No active qualifications found.")
        return

    # 기존 (qual_id, chunk_index) -> content_hash (변경 여부 판단용)
    existing_hashes: dict[tuple[int, int], str] = {}
    try:
        db = SessionLocal()
        r = db.execute(text("""
            SELECT qual_id, chunk_index, content_hash FROM certificates_vectors
        """)).fetchall()
        for row in r:
            key = (row.qual_id, getattr(row, "chunk_index", 0) or 0)
            existing_hashes[key] = (row.content_hash or "")
        db.close()
    except Exception as e:
        logger.warning("Could not load existing content_hash (migration may not be applied): %s", e)

    logger.info("Building chunked content for %s qualifications (chunk_size=%s, overlap=%s)...",
                len(rows), CHUNK_SIZE, CHUNK_OVERLAP)
    all_chunks: list[dict] = []
    for r in rows:
        full_content = build_content(r)
        qual_name = (r.get("qual_name") or "").strip() or "자격"
        chunks = chunk_with_tag(full_content, qual_name)
        for idx, c in enumerate(chunks):
            h = content_hash(c)
            existing = existing_hashes.get((r["qual_id"], idx))
            all_chunks.append({
                "qual_id": r["qual_id"],
                "name": qual_name,
                "content": c,
                "content_hash": h,
                "chunk_index": idx,
                "metadata": json.dumps({"source": "populate_certificates_vectors", "qual_id": r["qual_id"], "chunk_index": idx}),
                "need_embed": existing != h,
            })

    to_embed = [x for x in all_chunks if x["need_embed"]]
    logger.info("Total chunks: %s, need new embedding: %s (unchanged: %s)",
                len(all_chunks), len(to_embed), len(all_chunks) - len(to_embed))

    if args.dry_run:
        logger.info("DRY RUN: would upsert %s rows. Sample:", len(all_chunks))
        for i, it in enumerate(all_chunks[:5]):
            logger.info("  [%s] qual_id=%s chunk_index=%s need_embed=%s content=%s...",
                       i, it["qual_id"], it["chunk_index"], it["need_embed"], (it["content"][:60] + "…"))
        return

    # qual_id별로 하나라도 need_embed면 해당 qual 전체 재처리 (DELETE 후 INSERT)
    qual_ids_to_refresh = {it["qual_id"] for it in all_chunks if it["need_embed"]}
    chunks_to_upsert = [c for c in all_chunks if c["qual_id"] in qual_ids_to_refresh]
    to_embed_items = [c for c in chunks_to_upsert if c["need_embed"]]

    # 변경된 청크만 배치 임베딩
    need_embed_texts = [x["content"] for x in to_embed_items]
    embedding_by_content: dict[str, list[float]] = {}
    for i in range(0, len(need_embed_texts), args.batch):
        batch_texts = need_embed_texts[i : i + args.batch]
        try:
            embs = get_embeddings_batch(batch_texts)
            for t, e in zip(batch_texts, embs):
                embedding_by_content[t] = e
        except Exception as ex:
            logger.exception("Embedding batch failed at offset %s: %s", i, ex)
            raise
        logger.info("Embedded %s/%s (changed chunks)", min(i + args.batch, len(need_embed_texts)), len(need_embed_texts))
        if i + args.batch < len(need_embed_texts):
            time.sleep(0.2)

    for it in to_embed_items:
        it["embedding"] = embedding_by_content.get(it["content"])

    # refresh 대상 qual 중 need_embed=False 청크는 기존 DB에서 embedding 로드하여 재사용
    existing_embeddings: dict[tuple[int, int], list[float]] = {}
    if chunks_to_upsert:
        db = SessionLocal()
        try:
            qids = list(qual_ids_to_refresh)
            rows = db.execute(text("""
                SELECT qual_id, chunk_index, embedding FROM certificates_vectors
                WHERE qual_id = ANY(:ids)
            """), {"ids": qids}).fetchall()
            for row in rows:
                key = (row.qual_id, getattr(row, "chunk_index", 0) or 0)
                emb = getattr(row, "embedding", None)
                if emb is not None:
                    if isinstance(emb, list):
                        existing_embeddings[key] = emb
                    elif isinstance(emb, str):
                        import ast
                        try:
                            existing_embeddings[key] = ast.literal_eval(emb)
                        except Exception:
                            pass
                    else:
                        existing_embeddings[key] = list(emb)
        except Exception as e:
            logger.warning("Could not load existing embeddings: %s", e)
        finally:
            db.close()

    for it in chunks_to_upsert:
        if it.get("embedding"):
            continue
        key = (it["qual_id"], it["chunk_index"])
        if key in existing_embeddings:
            it["embedding"] = existing_embeddings[key]
        else:
            # 새 청크인데 아직 embedding 없음 (방어)
            it["embedding"] = get_embeddings_batch([it["content"]])[0]

    if not qual_ids_to_refresh:
        logger.info("No qual_ids need refresh; skipping DB write.")
        return

    db = SessionLocal()
    try:
        if args.truncate:
            db.execute(text("TRUNCATE certificates_vectors"))
            db.commit()
            logger.info("TRUNCATE certificates_vectors done.")
        else:
            qids = list(qual_ids_to_refresh)
            for j in range(0, len(qids), 500):
                chunk = qids[j : j + 500]
                db.execute(text("DELETE FROM certificates_vectors WHERE qual_id = ANY(:ids)"), {"ids": chunk})
            db.commit()
            logger.info("Deleted certificates_vectors for %s qual_ids (refresh set).", len(qids))

        # INSERT: content_hash, chunk_index 포함 (migration 적용 시)
        insert_sql = text("""
            INSERT INTO certificates_vectors (qual_id, name, content, embedding, metadata, content_hash, chunk_index)
            VALUES (:qual_id, :name, :content, CAST(:embedding AS vector), CAST(:metadata AS jsonb), :content_hash, :chunk_index)
        """)
        for it in chunks_to_upsert:
            db.execute(insert_sql, {
                "qual_id": it["qual_id"],
                "name": it["name"],
                "content": it["content"],
                "embedding": str(it["embedding"]),
                "metadata": it["metadata"],
                "content_hash": it["content_hash"],
                "chunk_index": it["chunk_index"],
            })
        db.commit()
        logger.info("Inserted %s rows into certificates_vectors (qual_ids refreshed: %s).",
                    len(chunks_to_upsert), len(qual_ids_to_refresh))
    except Exception as e:
        db.rollback()
        logger.exception("DB error: %s", e)
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
