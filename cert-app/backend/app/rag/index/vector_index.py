"""
Vector 검색: 기존 pgvector + vector_service 사용 (OpenAI embedding).
로컬에서 경량 모델로 대체하려면 여기만 교체.
Dense 전용 query rewrite 옵션 지원 (use_rewrite=True 시 구조화 질의로 임베딩).
"""
from typing import List, Optional

from sqlalchemy.orm import Session


def get_vector_search(
    db: Session,
    query: str,
    top_k: int = 10,
    threshold: Optional[float] = None,
    use_rewrite: bool = True,
) -> List[tuple]:
    """
    pgvector 유사도 검색. (chunk_id, score) 형태로 반환.
    chunk_id는 qual_id:chunk_index 문자열.
    use_rewrite=True이면 dense 전용 rewrite 적용 후 임베딩(설정 RAG_DENSE_USE_QUERY_REWRITE 반영).
    """
    from app.services.vector_service import vector_service
    from app.rag.config import get_rag_settings
    from app.rag.utils.dense_query_rewrite import rewrite_for_dense

    settings = get_rag_settings()
    th = threshold if threshold is not None else settings.RAG_VECTOR_THRESHOLD
    vector_query = query
    if use_rewrite and getattr(settings, "RAG_DENSE_USE_QUERY_REWRITE", True):
        try:
            rewritten = rewrite_for_dense(query)
            if rewritten and rewritten.strip():
                vector_query = rewritten
        except Exception:
            if getattr(settings, "RAG_DENSE_QUERY_REWRITE_FALLBACK", True):
                vector_query = query
            else:
                raise
    results = vector_service.similarity_search(
        db,
        vector_query,
        limit=top_k,
        match_threshold=th,
    )
    out: List[tuple] = []
    for r in results:
        qual_id = r.get("qual_id")
        chunk_index = r.get("chunk_index", 0)
        chunk_id = f"{qual_id}:{chunk_index}" if qual_id is not None else ""
        score = float(r.get("similarity", 0.0))
        out.append((chunk_id, score))
    return out
