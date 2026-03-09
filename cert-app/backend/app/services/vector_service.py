"""
벡터 저장/검색 (RAG). content_hash로 변경분만 임베딩 호출.
컨텍스트 주입 최적화: 유사도 임계값으로 저관련 청크 필터링.
"""
import hashlib
import json
import logging
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.utils.ai import get_embedding

logger = logging.getLogger(__name__)


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
        dense_content: Optional[str] = None,
    ) -> None:
        """
        Insert or update vector data. qual_id가 있을 때 content_hash가 기존과 동일하면 임베딩 호출 생략.
        dense_content가 있으면 임베딩과 content_hash는 dense_content 기준; 없으면 content 기준.
        UNIQUE(qual_id, chunk_index) 적용 시 ON CONFLICT DO UPDATE 사용.
        """
        text_to_embed = ((dense_content or content) or "").strip() or (content or " ").strip() or " "
        if not text_to_embed or not text_to_embed.strip():
            text_to_embed = " "
        content_hash = _content_hash(text_to_embed)
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

        try:
            embedding = get_embedding(text_to_embed)
        except Exception as e:
            logger.exception("get_embedding failed for qual_id=%s chunk_index=%s", qual_id, chunk_index)
            raise
        if not embedding or not isinstance(embedding, list):
            raise ValueError("get_embedding returned empty or invalid embedding")
        dense_val = dense_content if dense_content else None
        if qual_id is not None:
            try:
                db.execute(text("""
                    INSERT INTO certificates_vectors (qual_id, name, content, dense_content, embedding, metadata, content_hash, chunk_index)
                    VALUES (:qual_id, :name, :content, :dense_content, CAST(:embedding AS vector), CAST(:metadata AS jsonb), :content_hash, :chunk_index)
                    ON CONFLICT (qual_id, chunk_index) DO UPDATE SET
                        name = EXCLUDED.name,
                        content = EXCLUDED.content,
                        dense_content = EXCLUDED.dense_content,
                        embedding = EXCLUDED.embedding,
                        metadata = EXCLUDED.metadata,
                        content_hash = EXCLUDED.content_hash,
                        updated_at = NOW()
                """), {
                    "qual_id": qual_id,
                    "name": name,
                    "content": content,
                    "dense_content": dense_val,
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
        include_content: bool = True,
        include_metadata: bool = True,
    ) -> List[Dict]:
        """
        벡터 유사도 검색 (코사인). match_threshold는 DB WHERE 절에서 적용.
        exclude_qual_ids: 이미 취득한 자격 등 검색 제외할 qual_id 목록.

        include_content / include_metadata:
            - False 로 두면 대용량 컬럼(content, metadata)을 실제로 읽지 않으므로
              Supabase/Postgres egress 비용이 크게 줄어든다.
            - RAG 파이프라인처럼 chunk_id·similarity만 필요할 때는 둘 다 False 권장.
        """
        from app.utils.ai import get_embedding
        q = (query_text or "").strip() or " "
        try:
            query_embedding = get_embedding(q)
        except Exception as e:
            logger.exception("get_embedding failed for similarity_search")
            raise
        if not query_embedding or not isinstance(query_embedding, list):
            return []
        max_distance = (1.0 - match_threshold) if (match_threshold is not None and match_threshold > 0) else 1.0

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
        return out


vector_service = VectorService()
