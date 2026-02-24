from typing import List, Optional, Dict
from sqlalchemy.orm import Session
from sqlalchemy import text
import json

from app.utils.ai import get_embedding


class VectorService:
    """벡터 저장/검색. OpenAI embedding은 app.utils.ai 싱글톤 사용."""

    def upsert_vector_data(self, db: Session, qual_id: int, name: str, content: str, metadata: Dict = None):
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
        
        # Note: Since vector_id is UUID default, ON CONFLICT (qual_id) would be better if we want one record per cert.
        # But we might have multiple law snippets per cert.
        db.execute(query, {
            "qual_id": qual_id,
            "name": name,
            "content": content,
            "embedding": str(embedding), # pgvector handles string format or list
            "metadata": json.dumps(metadata or {})
        })
        db.commit()

    def similarity_search(self, db: Session, query_text: str, limit: int = 5) -> List[Dict]:
        """Perform vector similarity search."""
        query_embedding = get_embedding(query_text)
        
        # Cosine similarity search
        sql = text("""
            SELECT v.qual_id, v.name, v.content, v.metadata,
                   (1 - (v.embedding <=> :embedding)) as similarity
            FROM certificates_vectors v
            ORDER BY v.embedding <=> :embedding
            LIMIT :limit
        """)
        
        results = db.execute(sql, {
            "embedding": str(query_embedding),
            "limit": limit
        }).fetchall()
        
        return [
            {
                "qual_id": r.qual_id,
                "name": r.name,
                "content": r.content,
                "similarity": float(r.similarity),
                "metadata": r.metadata
            } for r in results
        ]

vector_service = VectorService()
