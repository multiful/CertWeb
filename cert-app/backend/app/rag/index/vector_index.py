"""
Vector 검색: 기존 pgvector + vector_service 사용 (OpenAI embedding).
로컬에서 경량 모델로 대체하려면 여기만 교체.
Dense 전용 query rewrite 옵션 지원 (use_rewrite=True 시 구조화 질의로 임베딩).
재작성이 원문과 다를 때(기본 RAG_DUAL_VECTOR_RRF_WHEN=divergence) 원문+재작성 이중 검색 RRF로 회수 보강.
"""
from typing import Any, Dict, List, Optional, Tuple

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


def get_vector_searches_preembedded(
    db: Session,
    query_texts: List[str],
    embeddings: List[List[float]],
    top_k: int,
    threshold: Optional[float],
) -> List[List[Tuple[str, float]]]:
    """
    이미 계산된 임베딩으로 여러 번 pgvector 검색 (OpenAI 왕복 없음).
    hybrid multi-query / COT 등에서 배치 임베딩 후 사용.
    """
    if len(query_texts) != len(embeddings):
        raise ValueError("query_texts and embeddings length mismatch")
    from app.services.vector_service import vector_service
    from app.rag.config import get_rag_settings

    settings = get_rag_settings()
    th = threshold if threshold is not None else settings.RAG_VECTOR_THRESHOLD
    out: List[List[Tuple[str, float]]] = []
    for q, emb in zip(query_texts, embeddings):
        results = vector_service.similarity_search(
            db,
            (q or "").strip() or " ",
            limit=top_k,
            match_threshold=th,
            include_content=False,
            include_metadata=False,
            query_embedding=emb,
        )
        out.append(_chunk_id_score(results))
    return out


def get_vector_search(
    db: Session,
    query: str,
    top_k: int = 10,
    threshold: Optional[float] = None,
    use_rewrite: bool = True,
    query_vec: Optional[List[float]] = None,
    out_meta: Optional[Dict[str, Any]] = None,
) -> List[tuple]:
    """
    pgvector 유사도 검색. (chunk_id, score) 형태로 반환.
    chunk_id는 qual_id:chunk_index 문자열.
    use_rewrite=True이면 dense 전용 rewrite 적용 후 임베딩(설정 RAG_DENSE_USE_QUERY_REWRITE 반영).
    query_vec: 제공 시 해당 쿼리용 임베딩 재사용(평가 러너 등). 원문 query와 동일할 때만 사용.
    RAG_DUAL_VECTOR_RRF_WHEN: divergence(기본)이면 재작성≠원문일 때 원문+재작성 RRF 병합.
    out_meta: 호출 측 trace용. 키 예: use_rewrite_applied, dual_rrf, dual_mode, q_raw, q_rew (pre_retrieval_trace).
    """
    from app.services.vector_service import vector_service
    from app.rag.config import get_rag_settings
    from app.rag.utils.dense_query_rewrite import rewrite_for_dense, extract_slots_for_dense

    settings = get_rag_settings()
    th = threshold if threshold is not None else settings.RAG_VECTOR_THRESHOLD
    vector_query = query
    dual_mode = (getattr(settings, "RAG_DUAL_VECTOR_RRF_WHEN", "divergence") or "divergence").strip().lower()
    rewrite_applied = False
    legacy_non_it_signal = False
    if use_rewrite and getattr(settings, "RAG_DENSE_USE_QUERY_REWRITE", True):
        try:
            rewritten = rewrite_for_dense(query)
            if rewritten and rewritten.strip():
                vector_query = rewritten
                rewrite_applied = True
            if dual_mode == "legacy_non_it_only":
                try:
                    from app.rag.utils.dense_query_rewrite import _query_suggests_it_domain

                    slots = extract_slots_for_dense(query)
                    legacy_non_it_signal = not _query_suggests_it_domain(slots, query)
                except Exception:
                    pass
        except Exception:
            if getattr(settings, "RAG_DENSE_QUERY_REWRITE_FALLBACK", True):
                vector_query = query
            else:
                raise

    q_raw = (query or "").strip()
    q_rew = (vector_query or "").strip()
    if dual_mode == "off":
        use_dual_rrf = False
    elif dual_mode == "legacy_non_it_only":
        use_dual_rrf = bool(legacy_non_it_signal) and q_rew != q_raw and bool(q_raw)
    else:
        use_dual_rrf = q_rew != q_raw and bool(q_raw)

    if out_meta is not None:
        out_meta.update(
            {
                "use_rewrite": bool(use_rewrite),
                "rewrite_applied": rewrite_applied,
                "dual_mode": dual_mode,
                "dual_rrf": bool(use_dual_rrf),
                "q_raw_len": len(q_raw),
                "q_rew_len": len(q_rew),
            }
        )

    if use_dual_rrf:
        # 원문 + 재작성 이중 검색 후 RRF (임베딩은 배치 1회로 OpenAI 왕복 절감)
        # RAG 파이프라인에서는 content/metadata가 필요 없으므로 egress 절감을 위해 제외
        from app.utils.ai import get_embeddings_batch

        embs = get_embeddings_batch([q_raw, q_rew])
        raw_results = vector_service.similarity_search(
            db,
            q_raw,
            limit=top_k,
            match_threshold=th,
            include_content=False,
            include_metadata=False,
            query_embedding=embs[0],
        )
        rew_results = vector_service.similarity_search(
            db,
            q_rew,
            limit=top_k,
            match_threshold=th,
            include_content=False,
            include_metadata=False,
            query_embedding=embs[1],
        )
        list_a = _chunk_id_score(raw_results)
        list_b = _chunk_id_score(rew_results)
        merged = _rrf_merge_two(list_a, list_b, k=60)
        merged = merged[:top_k]
        return merged
    vec_kw = {"query_embedding": query_vec} if (query_vec is not None and vector_query == query) else {}
    results = vector_service.similarity_search(
        db,
        vector_query,
        limit=top_k,
        match_threshold=th,
        include_content=False,
        include_metadata=False,
        **vec_kw,
    )
    return _chunk_id_score(results)
