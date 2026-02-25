"""
RAG용 certificates_vectors 테이블을 DB의 qualification 데이터로 채웁니다.
자격명·유형·분야·NCS·시행기관·등급을 조합한 content로 임베딩 생성 후 INSERT.

실행: cert-app/backend 에서
  uv run python scripts/populate_certificates_vectors.py

옵션:
  --truncate   기존 certificates_vectors 전체 삭제 후 채우기 (기본: 기존 qual_id 행만 갱신)
  --batch N    임베딩 API 배치 크기 (기본 50)
  --dry-run    DB 쓰기 없이 content/건수만 출력
"""
import argparse
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


def build_content(row) -> str:
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
    parser = argparse.ArgumentParser(description="Populate certificates_vectors from qualification table")
    parser.add_argument("--truncate", action="store_true", help="TRUNCATE certificates_vectors before insert")
    parser.add_argument("--batch", type=int, default=50, help="Embedding batch size (default 50)")
    parser.add_argument("--dry-run", action="store_true", help="No DB write, only print counts and sample content")
    args = parser.parse_args()

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

    logger.info("Building content for %s qualifications...", len(rows))
    items = []
    for r in rows:
        content = build_content(r)
        items.append({
            "qual_id": r["qual_id"],
            "name": (r.get("qual_name") or "").strip() or "자격",
            "content": content,
            "metadata": json.dumps({"source": "populate_certificates_vectors", "qual_id": r["qual_id"]}),
        })

    if args.dry_run:
        logger.info("DRY RUN: would insert %s rows. Sample content:", len(items))
        for i, it in enumerate(items[:3]):
            logger.info("  [%s] qual_id=%s name=%s content=%s...", i, it["qual_id"], it["name"], it["content"][:80])
        return

    # Embed in batches
    all_embeddings = []
    for i in range(0, len(items), args.batch):
        batch_items = items[i : i + args.batch]
        batch_texts = [x["content"] for x in batch_items]
        try:
            emb = get_embeddings_batch(batch_texts)
            all_embeddings.extend(emb)
        except Exception as e:
            logger.exception("Embedding batch failed at offset %s: %s", i, e)
            raise
        logger.info("Embedded %s/%s", min(i + args.batch, len(items)), len(items))
        if i + args.batch < len(items):
            time.sleep(0.2)

    if len(all_embeddings) != len(items):
        logger.error("Embedding count mismatch: %s vs %s", len(all_embeddings), len(items))
        sys.exit(1)

    for i, it in enumerate(items):
        it["embedding"] = all_embeddings[i]

    db = SessionLocal()
    try:
        if args.truncate:
            db.execute(text("TRUNCATE certificates_vectors"))
            db.commit()
            logger.info("TRUNCATE certificates_vectors done.")
        else:
            # 기존 동일 qual_id 행 삭제 (한 qual당 1행으로 유지)
            qual_ids = list({it["qual_id"] for it in items})
            for j in range(0, len(qual_ids), 500):
                chunk = qual_ids[j : j + 500]
                db.execute(text("DELETE FROM certificates_vectors WHERE qual_id = ANY(:ids)"), {"ids": chunk})
            db.commit()
            logger.info("Deleted existing certificates_vectors rows for %s qual_ids.", len(qual_ids))

        insert_sql = text("""
            INSERT INTO certificates_vectors (qual_id, name, content, embedding, metadata)
            VALUES (:qual_id, :name, :content, CAST(:embedding AS vector), CAST(:metadata AS jsonb))
        """)
        for it in items:
            db.execute(insert_sql, {
                "qual_id": it["qual_id"],
                "name": it["name"],
                "content": it["content"],
                "embedding": str(it["embedding"]),
                "metadata": it["metadata"],
            })
        db.commit()
        logger.info("Inserted %s rows into certificates_vectors. RAG 검색 품질이 개선됩니다.", len(items))
    except Exception as e:
        db.rollback()
        logger.exception("DB error: %s", e)
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
