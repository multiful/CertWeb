"""
Vector 검색: 기존 pgvector + vector_service 사용 (OpenAI embedding).
로컬에서 경량 모델로 대체하려면 여기만 교체.
Dense 전용 query rewrite 옵션 지원 (use_rewrite=True 시 구조화 질의로 임베딩).
비IT 쿼리 시 원문+재작성 이중 검색 RRF로 벡터 강화.
"""
from typing import List, Optional, Tuple

from sqlalchemy.orm import Session


def _chunk_id_score(results: List[dict]) -> List[Tuple[str, float]]:
    """vector_service 결과를 (chunk_id, score) 리스트로 변환."""
    out: List[Tuple[str, float]] = []
    for r in results:
        qual_id = r.get("qual_id")
        chunk_index = r.get("chunk_index", 0)
        chunk_id = f"{qual_id}:{chunk_index}" if qual_id is not None else ""
        score = float(r.get("similarity", 0.0))
        out.append((chunk_id, score))
    return out


def _rrf_merge_two(
    list_a: List[Tuple[str, float]],
    list_b: List[Tuple[str, float]],
    k: int = 60,
) -> List[Tuple[str, float]]:
    """두 (chunk_id, score) 리스트를 RRF로 병합. 반환은 (chunk_id, rrf_score) 상위 유지."""
    from collections import defaultdict
    rrf = defaultdict(float)
    for rank, (cid, _) in enumerate(list_a, start=1):
        rrf[cid] += 1.0 / (k + rank)
    for rank, (cid, _) in enumerate(list_b, start=1):
        rrf[cid] += 1.0 / (k + rank)
    sorted_ids = sorted(rrf.keys(), key=lambda c: rrf[c], reverse=True)
    return [(c, rrf[c]) for c in sorted_ids]


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
    비IT 쿼리일 때는 원문 + 재작성 두 번 검색 후 RRF 병합하여 벡터 강화.
    """
    from app.services.vector_service import vector_service
    from app.rag.config import get_rag_settings
    from app.rag.utils.dense_query_rewrite import rewrite_for_dense, extract_slots_for_dense

    settings = get_rag_settings()
    th = threshold if threshold is not None else settings.RAG_VECTOR_THRESHOLD
    vector_query = query
    is_non_it = False
    if use_rewrite and getattr(settings, "RAG_DENSE_USE_QUERY_REWRITE", True):
        try:
            rewritten = rewrite_for_dense(query)
            if rewritten and rewritten.strip():
                vector_query = rewritten
            # 비IT 여부: 슬롯 기준으로 판단 (IT 보조 키워드 미추가인 경우)
            try:
                from app.rag.utils.dense_query_rewrite import _query_suggests_it_domain
                slots = extract_slots_for_dense(query)
                is_non_it = not _query_suggests_it_domain(slots, query)
            except Exception:
                pass
        except Exception:
            if getattr(settings, "RAG_DENSE_QUERY_REWRITE_FALLBACK", True):
                vector_query = query
            else:
                raise

    if is_non_it and vector_query != query and query.strip():
        # 비IT: 원문 검색 + 재작성 검색 후 RRF 병합
        raw_results = vector_service.similarity_search(db, query.strip(), limit=top_k, match_threshold=th)
        rew_results = vector_service.similarity_search(db, vector_query, limit=top_k, match_threshold=th)
        list_a = _chunk_id_score(raw_results)
        list_b = _chunk_id_score(rew_results)
        merged = _rrf_merge_two(list_a, list_b, k=60)
        merged = merged[:top_k]
        return merged
    results = vector_service.similarity_search(
        db,
        vector_query,
        limit=top_k,
        match_threshold=th,
    )
    return _chunk_id_score(results)
