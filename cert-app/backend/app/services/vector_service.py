"""
벡터 저장/검색 (RAG). content_hash로 변경분만 임베딩 호출.
컨텍스트 주입 최적화: 유사도 임계값으로 저관련 청크 필터링.
"""
import hashlib
import json
import logging
import threading
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.utils.ai import get_embedding, get_embeddings_batch
from app.config import get_settings
from app.redis_client import redis_client
from app.rag.ingest.canonical_text import normalize_text_for_embedding

logger = logging.getLogger(__name__)
settings = get_settings()
_schema_cache_lock = threading.Lock()
_has_dense_content_cache: Optional[bool] = None
_has_bm25_text_cache: Optional[bool] = None


def _certificates_vectors_has_dense_content_column(db: Session) -> bool:
    """
    certificates_vectors.dense_content 컬럼 존재 여부를 1회 조회 후 캐시.
    스키마 조회 실패 시 보수적으로 False 처리.
    """
    global _has_dense_content_cache
    if _has_dense_content_cache is not None:
        return _has_dense_content_cache
    with _schema_cache_lock:
        if _has_dense_content_cache is not None:
            return _has_dense_content_cache
        try:
            row = db.execute(
                text(
                    """
                    SELECT 1
                    FROM information_schema.columns
                    WHERE table_name = 'certificates_vectors'
                      AND column_name = 'dense_content'
                    LIMIT 1
                    """
                )
            ).fetchone()
            _has_dense_content_cache = bool(row)
        except Exception:
            logger.exception("failed to inspect certificates_vectors schema for dense_content")
            _has_dense_content_cache = False
        return _has_dense_content_cache


def _certificates_vectors_has_bm25_text_column(db: Session) -> bool:
    """certificates_vectors.bm25_text (Indexing_opt text_for_sparse) 존재 여부 캐시."""
    global _has_bm25_text_cache
    if _has_bm25_text_cache is not None:
        return _has_bm25_text_cache
    with _schema_cache_lock:
        if _has_bm25_text_cache is not None:
            return _has_bm25_text_cache
        try:
            row = db.execute(
                text(
                    """
                    SELECT 1
                    FROM information_schema.columns
                    WHERE table_name = 'certificates_vectors'
                      AND column_name = 'bm25_text'
                    LIMIT 1
                    """
                )
            ).fetchone()
            _has_bm25_text_cache = bool(row)
        except Exception:
            logger.exception("failed to inspect certificates_vectors schema for bm25_text")
            _has_bm25_text_cache = False
        return _has_bm25_text_cache


def _content_hash(content: str) -> str:
    """SHA-256 해시. 변경 시에만 임베딩 호출용."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def invalidate_certificates_vectors_schema_cache() -> None:
    """DB 마이그레이션 직후 등 dense_content/bm25_text 컬럼 가용성이 바뀌었을 때 캐시 무효화."""
    global _has_dense_content_cache, _has_bm25_text_cache
    with _schema_cache_lock:
        _has_dense_content_cache = None
        _has_bm25_text_cache = None


class VectorService:
    """벡터 저장/검색. OpenAI embedding은 app.utils.ai 싱글톤 사용."""

    def upsert_vector_data(
        self,
        db: Session,
        qual_id: Optional[int],
        name: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        chunk_index: int = 0,
        dense_content: Optional[str] = None,
        bm25_text: Optional[str] = None,
    ) -> None:
        """
        Insert or update vector data. qual_id가 있을 때 content_hash가 기존과 동일하면 임베딩 호출 생략.
        dense_content가 있으면 임베딩과 content_hash는 dense_content 기준; 없으면 content 기준.
        bm25_text 컬럼이 있으면 배치와 동일하게 해시 동일·본문 불변 시 bm25만 갱신 가능.
        UNIQUE(qual_id, chunk_index) 적용 시 ON CONFLICT DO UPDATE 사용.
        """
        text_to_embed = normalize_text_for_embedding((dense_content or content) or "") or " "
        if not text_to_embed or not text_to_embed.strip():
            text_to_embed = " "
        content_hash = _content_hash(text_to_embed)
        bm25_norm = normalize_text_for_embedding(str(bm25_text)) if bm25_text is not None else None
        has_bm25 = _certificates_vectors_has_bm25_text_column(db)

        if qual_id is not None:
            try:
                if has_bm25:
                    row = db.execute(
                        text(
                            """
                            SELECT content_hash, COALESCE(bm25_text, '') AS bm25_text
                            FROM certificates_vectors
                            WHERE qual_id = :qual_id AND chunk_index = :chunk_index
                            """
                        ),
                        {"qual_id": qual_id, "chunk_index": chunk_index},
                    ).fetchone()
                else:
                    row = db.execute(
                        text(
                            """
                            SELECT content_hash FROM certificates_vectors
                            WHERE qual_id = :qual_id AND chunk_index = :chunk_index
                            """
                        ),
                        {"qual_id": qual_id, "chunk_index": chunk_index},
                    ).fetchone()
                if row and getattr(row, "content_hash", None) == content_hash:
                    if has_bm25 and bm25_norm is not None:
                        old_bm = getattr(row, "bm25_text", None) or ""
                        if old_bm != bm25_norm:
                            db.execute(
                                text(
                                    """
                                    UPDATE certificates_vectors
                                    SET bm25_text = :bm25_text,
                                        metadata = CAST(:metadata AS jsonb),
                                        updated_at = NOW()
                                    WHERE qual_id = :qual_id AND chunk_index = :chunk_index
                                    """
                                ),
                                {
                                    "bm25_text": bm25_norm,
                                    "metadata": json.dumps(metadata or {}),
                                    "qual_id": qual_id,
                                    "chunk_index": chunk_index,
                                },
                            )
                            db.commit()
                    return
            except Exception:
                logger.exception("upsert_vector_data hash/bm25 pre-check failed qual_id=%s", qual_id)

        try:
            embedding = get_embedding(text_to_embed)
        except Exception:
            logger.exception("get_embedding failed for qual_id=%s chunk_index=%s", qual_id, chunk_index)
            raise
        if not embedding or not isinstance(embedding, list):
            raise ValueError("get_embedding returned empty or invalid embedding")
        dense_val = normalize_text_for_embedding(dense_content) if dense_content else None
        has_dense_content = _certificates_vectors_has_dense_content_column(db)
        meta_js = json.dumps(metadata or {})
        if qual_id is not None:
            payload = {
                "qual_id": qual_id,
                "name": name,
                "content": content,
                "dense_content": dense_val,
                "bm25_text": bm25_norm,
                "embedding": str(embedding),
                "metadata": meta_js,
                "content_hash": content_hash,
                "chunk_index": chunk_index,
            }
            if has_dense_content and has_bm25:
                db.execute(
                    text(
                        """
                        INSERT INTO certificates_vectors
                            (qual_id, name, content, dense_content, bm25_text, embedding, metadata, content_hash, chunk_index)
                        VALUES
                            (:qual_id, :name, :content, :dense_content, :bm25_text, CAST(:embedding AS vector), CAST(:metadata AS jsonb), :content_hash, :chunk_index)
                        ON CONFLICT (qual_id, chunk_index) DO UPDATE SET
                            name = EXCLUDED.name,
                            content = EXCLUDED.content,
                            dense_content = EXCLUDED.dense_content,
                            bm25_text = EXCLUDED.bm25_text,
                            embedding = EXCLUDED.embedding,
                            metadata = EXCLUDED.metadata,
                            content_hash = EXCLUDED.content_hash,
                            updated_at = NOW()
                        """
                    ),
                    payload,
                )
            elif has_dense_content:
                db.execute(
                    text(
                        """
                        INSERT INTO certificates_vectors
                            (qual_id, name, content, dense_content, embedding, metadata, content_hash, chunk_index)
                        VALUES
                            (:qual_id, :name, :content, :dense_content, CAST(:embedding AS vector), CAST(:metadata AS jsonb), :content_hash, :chunk_index)
                        ON CONFLICT (qual_id, chunk_index) DO UPDATE SET
                            name = EXCLUDED.name,
                            content = EXCLUDED.content,
                            dense_content = EXCLUDED.dense_content,
                            embedding = EXCLUDED.embedding,
                            metadata = EXCLUDED.metadata,
                            content_hash = EXCLUDED.content_hash,
                            updated_at = NOW()
                        """
                    ),
                    {k: v for k, v in payload.items() if k != "bm25_text"},
                )
            elif has_bm25:
                db.execute(
                    text(
                        """
                        INSERT INTO certificates_vectors
                            (qual_id, name, content, bm25_text, embedding, metadata, content_hash, chunk_index)
                        VALUES
                            (:qual_id, :name, :content, :bm25_text, CAST(:embedding AS vector), CAST(:metadata AS jsonb), :content_hash, :chunk_index)
                        ON CONFLICT (qual_id, chunk_index) DO UPDATE SET
                            name = EXCLUDED.name,
                            content = EXCLUDED.content,
                            bm25_text = EXCLUDED.bm25_text,
                            embedding = EXCLUDED.embedding,
                            metadata = EXCLUDED.metadata,
                            content_hash = EXCLUDED.content_hash,
                            updated_at = NOW()
                        """
                    ),
                    payload,
                )
            else:
                db.execute(
                    text(
                        """
                        INSERT INTO certificates_vectors
                            (qual_id, name, content, embedding, metadata, content_hash, chunk_index)
                        VALUES
                            (:qual_id, :name, :content, CAST(:embedding AS vector), CAST(:metadata AS jsonb), :content_hash, :chunk_index)
                        ON CONFLICT (qual_id, chunk_index) DO UPDATE SET
                            name = EXCLUDED.name,
                            content = EXCLUDED.content,
                            embedding = EXCLUDED.embedding,
                            metadata = EXCLUDED.metadata,
                            content_hash = EXCLUDED.content_hash,
                            updated_at = NOW()
                        """
                    ),
                    {k: v for k, v in payload.items() if k != "bm25_text"},
                )
        else:
            db.execute(
                text(
                    """
                    INSERT INTO certificates_vectors (qual_id, name, content, embedding, metadata)
                    VALUES (:qual_id, :name, :content, CAST(:embedding AS vector), CAST(:metadata AS jsonb))
                    """
                ),
                {
                    "qual_id": qual_id,
                    "name": name,
                    "content": content,
                    "embedding": str(embedding),
                    "metadata": meta_js,
                },
            )
        db.commit()

    def upsert_vector_data_batch(
        self,
        db: Session,
        rows: List[Dict[str, Any]],
    ) -> Tuple[int, int, int]:
        """
        배치 upsert:
        - 변경 없음(content_hash 동일) 항목은 임베딩 스킵
        - 해시 동일이어도 bm25_text만 바뀐 경우: 임베딩 없이 bm25_text/metadata만 UPDATE (API 비용 절감)
        반환: (embedding_upsert_count, skipped_count, sparse_only_patch_count)
        """
        if not rows:
            return (0, 0, 0)

        has_bm25 = _certificates_vectors_has_bm25_text_column(db)
        prepared: List[Dict[str, Any]] = []
        skipped = 0
        bm25_patches: List[Dict[str, Any]] = []

        for row in rows:
            qual_id = row.get("qual_id")
            chunk_index = int(row.get("chunk_index", 0) or 0)
            content = str(row.get("content") or "")
            dense_content = row.get("dense_content")
            text_to_embed = normalize_text_for_embedding((dense_content or content) or "") or " "
            content_hash = _content_hash(text_to_embed)

            raw_bm25 = row.get("bm25_text")
            bm25_text: Optional[str] = None
            if raw_bm25 is not None:
                bm25_text = normalize_text_for_embedding(str(raw_bm25)) or None

            if qual_id is not None:
                try:
                    if has_bm25:
                        existing = db.execute(
                            text(
                                """
                                SELECT content_hash, COALESCE(bm25_text, '') AS bm25_text
                                FROM certificates_vectors
                                WHERE qual_id = :qual_id AND chunk_index = :chunk_index
                                """
                            ),
                            {"qual_id": int(qual_id), "chunk_index": chunk_index},
                        ).fetchone()
                    else:
                        existing = db.execute(
                            text(
                                """
                                SELECT content_hash FROM certificates_vectors
                                WHERE qual_id = :qual_id AND chunk_index = :chunk_index
                                """
                            ),
                            {"qual_id": int(qual_id), "chunk_index": chunk_index},
                        ).fetchone()
                    if existing and getattr(existing, "content_hash", None) == content_hash:
                        if has_bm25 and bm25_text is not None:
                            old_bm = getattr(existing, "bm25_text", None) or ""
                            if old_bm != bm25_text:
                                bm25_patches.append(
                                    {
                                        "qual_id": int(qual_id),
                                        "chunk_index": chunk_index,
                                        "bm25_text": bm25_text,
                                        "metadata": json.dumps(row.get("metadata") or {}),
                                    }
                                )
                            else:
                                skipped += 1
                        else:
                            skipped += 1
                        continue
                except Exception:
                    pass

            prepared.append(
                {
                    "qual_id": qual_id,
                    "chunk_index": chunk_index,
                    "name": str(row.get("name") or ""),
                    "content": content,
                    "dense_content": normalize_text_for_embedding(dense_content) if dense_content else None,
                    "bm25_text": bm25_text,
                    "metadata": row.get("metadata") or {},
                    "text_to_embed": text_to_embed,
                    "content_hash": content_hash,
                }
            )

        sparse_patched = 0
        try:
            for p in bm25_patches:
                db.execute(
                    text(
                        """
                        UPDATE certificates_vectors
                        SET bm25_text = :bm25_text,
                            metadata = CAST(:metadata AS jsonb),
                            updated_at = NOW()
                        WHERE qual_id = :qual_id AND chunk_index = :chunk_index
                        """
                    ),
                    p,
                )
                sparse_patched += 1

            if not prepared:
                db.commit()
                logger.debug(
                    "upsert_vector_data_batch: sparse_only=%s skipped=%s",
                    sparse_patched,
                    skipped,
                )
                return (0, skipped, sparse_patched)

            embeddings = get_embeddings_batch([r["text_to_embed"] for r in prepared])
        except Exception:
            logger.exception("get_embeddings_batch failed: rows=%s", len(prepared))
            raise
        if not isinstance(embeddings, list) or len(embeddings) != len(prepared):
            logger.error(
                "embedding batch size mismatch: prepared=%s got=%s",
                len(prepared),
                len(embeddings) if isinstance(embeddings, list) else "invalid",
            )
            raise ValueError("embedding batch size mismatch")
        has_dense_content = _certificates_vectors_has_dense_content_column(db)

        updated = 0
        try:
            for r, emb in zip(prepared, embeddings):
                qual_id = r["qual_id"]
                payload = {
                    "qual_id": qual_id,
                    "name": r["name"],
                    "content": r["content"],
                    "dense_content": r["dense_content"],
                    "bm25_text": r.get("bm25_text"),
                    "embedding": str(emb),
                    "metadata": json.dumps(r["metadata"]),
                    "content_hash": r["content_hash"],
                    "chunk_index": r["chunk_index"],
                }
                if qual_id is not None:
                    if has_dense_content and has_bm25:
                        db.execute(
                            text(
                                """
                                INSERT INTO certificates_vectors
                                    (qual_id, name, content, dense_content, bm25_text, embedding, metadata, content_hash, chunk_index)
                                VALUES
                                    (:qual_id, :name, :content, :dense_content, :bm25_text, CAST(:embedding AS vector), CAST(:metadata AS jsonb), :content_hash, :chunk_index)
                                ON CONFLICT (qual_id, chunk_index) DO UPDATE SET
                                    name = EXCLUDED.name,
                                    content = EXCLUDED.content,
                                    dense_content = EXCLUDED.dense_content,
                                    bm25_text = EXCLUDED.bm25_text,
                                    embedding = EXCLUDED.embedding,
                                    metadata = EXCLUDED.metadata,
                                    content_hash = EXCLUDED.content_hash,
                                    updated_at = NOW()
                                """
                            ),
                            payload,
                        )
                    elif has_dense_content:
                        db.execute(
                            text(
                                """
                                INSERT INTO certificates_vectors
                                    (qual_id, name, content, dense_content, embedding, metadata, content_hash, chunk_index)
                                VALUES
                                    (:qual_id, :name, :content, :dense_content, CAST(:embedding AS vector), CAST(:metadata AS jsonb), :content_hash, :chunk_index)
                                ON CONFLICT (qual_id, chunk_index) DO UPDATE SET
                                    name = EXCLUDED.name,
                                    content = EXCLUDED.content,
                                    dense_content = EXCLUDED.dense_content,
                                    embedding = EXCLUDED.embedding,
                                    metadata = EXCLUDED.metadata,
                                    content_hash = EXCLUDED.content_hash,
                                    updated_at = NOW()
                                """
                            ),
                            {k: v for k, v in payload.items() if k != "bm25_text"},
                        )
                    elif has_bm25:
                        db.execute(
                            text(
                                """
                                INSERT INTO certificates_vectors
                                    (qual_id, name, content, bm25_text, embedding, metadata, content_hash, chunk_index)
                                VALUES
                                    (:qual_id, :name, :content, :bm25_text, CAST(:embedding AS vector), CAST(:metadata AS jsonb), :content_hash, :chunk_index)
                                ON CONFLICT (qual_id, chunk_index) DO UPDATE SET
                                    name = EXCLUDED.name,
                                    content = EXCLUDED.content,
                                    bm25_text = EXCLUDED.bm25_text,
                                    embedding = EXCLUDED.embedding,
                                    metadata = EXCLUDED.metadata,
                                    content_hash = EXCLUDED.content_hash,
                                    updated_at = NOW()
                                """
                            ),
                            payload,
                        )
                    else:
                        db.execute(
                            text(
                                """
                                INSERT INTO certificates_vectors
                                    (qual_id, name, content, embedding, metadata, content_hash, chunk_index)
                                VALUES
                                    (:qual_id, :name, :content, CAST(:embedding AS vector), CAST(:metadata AS jsonb), :content_hash, :chunk_index)
                                ON CONFLICT (qual_id, chunk_index) DO UPDATE SET
                                    name = EXCLUDED.name,
                                    content = EXCLUDED.content,
                                    embedding = EXCLUDED.embedding,
                                    metadata = EXCLUDED.metadata,
                                    content_hash = EXCLUDED.content_hash,
                                    updated_at = NOW()
                                """
                            ),
                            {k: v for k, v in payload.items() if k != "bm25_text"},
                        )
                else:
                    db.execute(
                        text(
                            """
                            INSERT INTO certificates_vectors (qual_id, name, content, embedding, metadata)
                            VALUES (:qual_id, :name, :content, CAST(:embedding AS vector), CAST(:metadata AS jsonb))
                            """
                        ),
                        payload,
                    )
                updated += 1
            db.commit()
            logger.debug(
                "upsert_vector_data_batch committed: updated=%s skipped=%s sparse_patched=%s",
                updated,
                skipped,
                sparse_patched,
            )
            return (updated, skipped, sparse_patched)
        except Exception:
            db.rollback()
            logger.exception("upsert_vector_data_batch failed and rolled back: rows=%s", len(prepared))
            raise

    def similarity_search(
        self,
        db: Session,
        query_text: str,
        limit: int = 5,
        match_threshold: Optional[float] = None,
        exclude_qual_ids: Optional[List[int]] = None,
        include_content: bool = False,
        include_metadata: bool = False,
        query_embedding: Optional[List[float]] = None,
    ) -> List[Dict]:
        """
        벡터 유사도 검색 (코사인). match_threshold는 DB WHERE 절에서 적용.
        exclude_qual_ids: 이미 취득한 자격 등 검색 제외할 qual_id 목록.
        query_embedding: 제공 시 get_embedding 호출 생략(평가 러너 등에서 재사용).

        include_content / include_metadata:
            - False 로 두면 대용량 컬럼(content, metadata)을 실제로 읽지 않으므로
              Supabase/Postgres egress 비용이 크게 줄어든다.
            - RAG 파이프라인처럼 chunk_id·similarity만 필요할 때는 둘 다 False 권장.
        """
        from app.utils.ai import get_embedding
        if query_embedding is not None and isinstance(query_embedding, list) and len(query_embedding) > 0:
            pass  # 호출자 제공 임베딩 재사용 (평가 러너 등)
        else:
            q = (query_text or "").strip() or " "
            try:
                query_embedding = get_embedding(q)
            except Exception as e:
                logger.exception("get_embedding failed for similarity_search")
                raise
        if not query_embedding or not isinstance(query_embedding, list):
            return []
        max_distance = (1.0 - match_threshold) if (match_threshold is not None and match_threshold > 0) else 1.0

        # Redis가 연결되어 있으면 similarity_search 결과를 TTL 캐시해 재질의 비용을 줄인다.
        cache_key: Optional[str] = None
        if redis_client.is_connected():
            try:
                # embedding 리스트는 길어질 수 있으므로 직접 문자열로 넣기보다는 해시를 사용
                params_for_hash: Dict[str, Any] = {
                    "q": (query_text or "").strip(),
                    "max_distance": max_distance,
                    "limit": limit,
                    "exclude_ids": tuple(exclude_qual_ids or []),
                    "include_content": include_content,
                    "include_metadata": include_metadata,
                    "has_query_embedding": bool(query_embedding),
                }
                h = redis_client.hash_query_params(**params_for_hash)
                cache_key = f"vec:search:v1:{h}"
                cached = redis_client.get(cache_key)
                if isinstance(cached, list):
                    return cached
            except Exception:
                # 캐시 문제가 있어도 검색 자체는 계속 진행
                cache_key = None

        # Egress 최적화를 위해 대용량 컬럼 선택 여부를 동적으로 결정
        select_columns = [
            "v.qual_id",
            "v.name",
            "COALESCE(v.chunk_index, 0) as chunk_index",
            "(1 - (v.embedding <=> :embedding)) as similarity",
        ]
        if include_content:
            select_columns.insert(2, "v.content")  # name 뒤에 content 배치
        else:
            select_columns.insert(2, "NULL::text as content")
        if include_metadata:
            select_columns.insert(3, "v.metadata")
        else:
            select_columns.insert(3, "NULL::jsonb as metadata")

        sql = text("""
            SELECT {cols}
            FROM certificates_vectors v
            WHERE (v.embedding <=> :embedding) <= :max_distance
            {exclude_clause}
            ORDER BY v.embedding <=> :embedding
            LIMIT :limit
        """.format(
            cols=", ".join(select_columns),
            exclude_clause="AND v.qual_id != ALL(:exclude_ids)" if exclude_qual_ids else ""
        ))
        params = {
            "embedding": str(query_embedding),  # pgvector 형식
            "max_distance": max_distance,
            "limit": limit,
        }
        if exclude_qual_ids:
            params["exclude_ids"] = exclude_qual_ids

        results = db.execute(sql, params).fetchall()
        out: List[Dict[str, Any]] = []
        for r in results:
            item: Dict[str, Any] = {
                "qual_id": r.qual_id,
                "name": r.name,
                "similarity": float(r.similarity),
                "chunk_index": getattr(r, "chunk_index", 0) or 0,
            }
            # content / metadata는 선택적으로만 포함
            if include_content:
                item["content"] = getattr(r, "content", None)
            if include_metadata:
                item["metadata"] = getattr(r, "metadata", None)
            out.append(item)
        # 검색 결과를 Redis에 TTL 캐시 (RAG 응답 TTL과 동일하게 사용)
        if cache_key:
            try:
                redis_client.set(cache_key, out, ttl=settings.CACHE_TTL_RAG)
            except Exception:
                pass
        return out


vector_service = VectorService()
