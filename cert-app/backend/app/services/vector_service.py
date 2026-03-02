"""
벡터 저장/검색 (RAG). content_hash로 변경분만 임베딩 호출.
컨텍스트 주입 최적화: 유사도 임계값으로 저관련 청크 필터링.
"""
import hashlib
import json
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.utils.ai import get_embedding


def _content_hash(content: str) -> str:
    """SHA-256 해시. 변경 시에만 임베딩 호출용."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


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
    ) -> None:
        """
        Insert or update vector data. qual_id가 있을 때 content_hash가 기존과 동일하면 임베딩 호출 생략.
        UNIQUE(qual_id, chunk_index) 적용 시 ON CONFLICT DO UPDATE 사용.
        qual_id=None(예: law_update_pipeline)인 경우 항상 임베딩 후 INSERT.
        """
        content_hash = _content_hash(content)
        if qual_id is not None:
            try:
                row = db.execute(
                    text("""
                        SELECT content_hash FROM certificates_vectors
                        WHERE qual_id = :qual_id AND chunk_index = :chunk_index
                    """),
                    {"qual_id": qual_id, "chunk_index": chunk_index},
                ).fetchone()
                if row and getattr(row, "content_hash", None) == content_hash:
                    return
            except Exception:
                pass

        embedding = get_embedding(content)
        if qual_id is not None:
            try:
                db.execute(text("""
                    INSERT INTO certificates_vectors (qual_id, name, content, embedding, metadata, content_hash, chunk_index)
                    VALUES (:qual_id, :name, :content, CAST(:embedding AS vector), CAST(:metadata AS jsonb), :content_hash, :chunk_index)
                    ON CONFLICT (qual_id, chunk_index) DO UPDATE SET
                        name = EXCLUDED.name,
                        content = EXCLUDED.content,
                        embedding = EXCLUDED.embedding,
                        metadata = EXCLUDED.metadata,
                        content_hash = EXCLUDED.content_hash,
                        updated_at = NOW()
                """), {
                    "qual_id": qual_id,
                    "name": name,
                    "content": content,
                    "embedding": str(embedding),
                    "metadata": json.dumps(metadata or {}),
                    "content_hash": content_hash,
                    "chunk_index": chunk_index,
                })
            except Exception:
                db.execute(text("""
                    INSERT INTO certificates_vectors (qual_id, name, content, embedding, metadata)
                    VALUES (:qual_id, :name, :content, CAST(:embedding AS vector), CAST(:metadata AS jsonb))
                """), {
                    "qual_id": qual_id,
                    "name": name,
                    "content": content,
                    "embedding": str(embedding),
                    "metadata": json.dumps(metadata or {}),
                })
        else:
            db.execute(text("""
                INSERT INTO certificates_vectors (qual_id, name, content, embedding, metadata)
                VALUES (:qual_id, :name, :content, CAST(:embedding AS vector), CAST(:metadata AS jsonb))
            """), {
                "qual_id": qual_id,
                "name": name,
                "content": content,
                "embedding": str(embedding),
                "metadata": json.dumps(metadata or {}),
            })
        db.commit()

    def similarity_search(
        self,
        db: Session,
        query_text: str,
        limit: int = 5,
        match_threshold: Optional[float] = None,
        exclude_qual_ids: Optional[List[int]] = None,
    ) -> List[Dict]:
        """
        벡터 유사도 검색 (코사인). match_threshold는 DB WHERE 절에서 적용.
        exclude_qual_ids: 이미 취득한 자격 등 검색 제외할 qual_id 목록.
        """
        from app.utils.ai import get_embedding
        query_embedding = get_embedding(query_text)
        max_distance = (1.0 - match_threshold) if (match_threshold is not None and match_threshold > 0) else 1.0

        sql = text("""
            SELECT v.qual_id, v.name, v.content, v.metadata,
                   (1 - (v.embedding <=> :embedding)) as similarity
            FROM certificates_vectors v
            WHERE (v.embedding <=> :embedding) <= :max_distance
            {exclude_clause}
            ORDER BY v.embedding <=> :embedding
            LIMIT :limit
        """.format(
            exclude_clause="AND v.qual_id != ALL(:exclude_ids)" if exclude_qual_ids else ""
        ))
        params = {
            "embedding": str(query_embedding),
            "max_distance": max_distance,
            "limit": limit,
        }
        if exclude_qual_ids:
            params["exclude_ids"] = exclude_qual_ids

        results = db.execute(sql, params).fetchall()
        return [
            {
                "qual_id": r.qual_id,
                "name": r.name,
                "content": r.content,
                "similarity": float(r.similarity),
                "metadata": r.metadata,
            }
            for r in results
        ]


vector_service = VectorService()
