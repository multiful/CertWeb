"""
벡터 저장/검색 (RAG). 컨텍스트 주입 최적화: 유사도 임계값으로 저관련 청크 필터링.
"""
import json
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.utils.ai import get_embedding


class VectorService:
    """벡터 저장/검색. OpenAI embedding은 app.utils.ai 싱글톤 사용."""

    def upsert_vector_data(
        self,
        db: Session,
        qual_id: int,
        name: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Insert or update vector data."""
        embedding = get_embedding(content)
        query = text("""
            INSERT INTO certificates_vectors (qual_id, name, content, embedding, metadata)
            VALUES (:qual_id, :name, :content, :embedding, :metadata)
            ON CONFLICT (vector_id) DO UPDATE SET
                content = EXCLUDED.content,
                embedding = EXCLUDED.embedding,
                metadata = EXCLUDED.metadata,
                updated_at = NOW()
        """)
        db.execute(query, {
            "qual_id": qual_id,
            "name": name,
            "content": content,
            "embedding": str(embedding),
            "metadata": json.dumps(metadata or {})
        })
        db.commit()

    def similarity_search(
        self,
        db: Session,
        query_text: str,
        limit: int = 5,
        match_threshold: Optional[float] = None,
    ) -> List[Dict]:
        """
        벡터 유사도 검색 (코사인). match_threshold는 DB WHERE 절에서 적용해 불필요한 행 전송을 줄임.
        """
        query_embedding = get_embedding(query_text)
        # 코사인 거리 <=> 0~2. similarity = 1 - distance. threshold 이상 => distance <= 1 - threshold
        max_distance = (1.0 - match_threshold) if (match_threshold is not None and match_threshold > 0) else 1.0

        sql = text("""
            SELECT v.qual_id, v.name, v.content, v.metadata,
                   (1 - (v.embedding <=> :embedding)) as similarity
            FROM certificates_vectors v
            WHERE (v.embedding <=> :embedding) <= :max_distance
            ORDER BY v.embedding <=> :embedding
            LIMIT :limit
        """)
        results = db.execute(sql, {
            "embedding": str(query_embedding),
            "max_distance": max_distance,
            "limit": limit,
        }).fetchall()
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
