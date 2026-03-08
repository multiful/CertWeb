"""
고도화 RAG 단일 파이프라인: 가중치 RRF + 다중 질의 Sparse + 경량 리랭커.

- Dense: 벡터(임계값 0.3) 상위 TOP_PER_QUERY
- Sparse: expanded_q + 원문 query 각각 풀텍스트 검색 후 RRF로 병합
- 가중치 RRF: score = w_d * 1/(RRF_K+rank_dense) + w_s * 1/(RRF_K+rank_sparse)
- 경량 리랭커: RRF 상위 20건을 쿼리 토큰–name 겹침으로 재정렬 후 top_k

ragas_eval.py, compare_rag_three_way.py 에서 공통 사용.
"""
from typing import List

from sqlalchemy import text
from sqlalchemy.orm import Session

TOP_PER_QUERY = 30
RRF_K = 60
RRF_K_SPARSE_INTERNAL = 30
ENHANCED_VECTOR_THRESHOLD = 0.3


def classify_query_and_expand(query: str) -> tuple[float, float, str]:
    """
    질의 타입에 따라 Dense/Sparse 가중치와 풀텍스트용 확장 질의를 결정.
    - w_d: Dense 가중치, w_s: Sparse 가중치
    - 키워드형(짧은 질의, 기사/산업기사/기능사, SQL, 컴퓨터): w_d=1.0, w_s=1.2
    - 그 외: w_d=1.3, w_s=0.7
    """
    q = (query or "").strip()
    base = q
    if "정보처리기사" in q:
        base = "정보처리기사 정보처리"
    elif q.upper() == "SQL" or "SQL" in q:
        base = "SQL 데이터베이스"
    elif "간호" in q:
        base = "간호사 간호"

    tokens = q.split()
    is_short = len(tokens) <= 2 and len(q) <= 8
    has_cert_suffix = any(s in q for s in ["기사", "산업기사", "기능사"])
    is_keywordy = is_short or has_cert_suffix or q.upper() == "SQL" or "컴퓨터" in q

    if is_keywordy:
        w_d, w_s = 1.0, 1.2
    else:
        w_d, w_s = 1.3, 0.7
    return w_d, w_s, base


def _sparse_rank_map_for_query(db: Session, q: str, limit: int) -> dict[int, int]:
    """풀텍스트 검색으로 qual_id -> rank(1-based) 맵 반환. 매칭 없으면 빈 dict."""
    try:
        ft_sql = text(
            """
            SELECT qual_id, name
            FROM certificates_vectors
            WHERE content_tsv @@ plainto_tsquery('simple', :q)
            ORDER BY ts_rank_cd(content_tsv, plainto_tsquery('simple', :q)) DESC
            LIMIT :limit
        """
        )
        ft_rows = db.execute(ft_sql, {"q": q, "limit": limit}).fetchall()
        seen = set()
        rank_list: list[int] = []
        for r in ft_rows:
            if r.qual_id not in seen:
                seen.add(r.qual_id)
                rank_list.append(r.qual_id)
        return {qid: i + 1 for i, qid in enumerate(rank_list)}
    except Exception:
        db.rollback()
        return {}


def _keyword_overlap_rerank(
    db: Session, qual_ids: list[int], query_tokens: List[str], top_k: int
) -> list[int]:
    """
    RRF 상위 후보를 쿼리 토큰이 name에 얼마나 포함되는지로 재정렬 (경량 리랭커).
    """
    if not qual_ids or not query_tokens:
        return qual_ids[:top_k]
    token_set = set(t.lower() for t in query_tokens if t.strip())
    if not token_set:
        return qual_ids[:top_k]
    sql = text(
        "SELECT qual_id, name FROM certificates_vectors WHERE qual_id = ANY(:ids)"
    )
    rows = db.execute(sql, {"ids": qual_ids}).fetchall()
    by_id = {r.qual_id: (getattr(r, "name", "") or "") for r in rows}
    name_lower = {qid: (name.lower() if name else "") for qid, name in by_id.items()}

    def count_hits(qid: int) -> int:
        s = name_lower.get(qid, "")
        return sum(1 for t in token_set if t in s)

    scored = [(qid, count_hits(qid)) for qid in qual_ids]
    scored.sort(key=lambda x: -x[1])
    return [qid for qid, _ in scored][:top_k]


def enhanced_rag_03_hybrid(
    db: Session,
    query: str,
    query_vec: list,
    top_k: int,
    w_d_override: float | None = None,
    w_s_override: float | None = None,
) -> list[int]:
    """
    고도화 RAG (가중치 RRF + 다중 질의 Sparse + 경량 리랭커).
    w_d_override, w_s_override 가 있으면 classify_query_and_expand 대신 해당 가중치 사용(랜덤 서치 등).
    """
    from app.rag.config import get_rag_settings
    max_dist = 1.0 - ENHANCED_VECTOR_THRESHOLD
    if w_d_override is not None and w_s_override is not None:
        w_d, w_s = w_d_override, w_s_override
        expanded_q = (query or "").strip()
        if "정보처리기사" in expanded_q:
            expanded_q = "정보처리기사 정보처리"
        elif expanded_q.upper() == "SQL" or "SQL" in expanded_q:
            expanded_q = "SQL 데이터베이스"
        elif "간호" in expanded_q:
            expanded_q = "간호사 간호"
    elif getattr(get_rag_settings(), "RAG_CURRENT_W_D", None) is not None and getattr(get_rag_settings(), "RAG_CURRENT_W_S", None) is not None:
        w_d = get_rag_settings().RAG_CURRENT_W_D
        w_s = get_rag_settings().RAG_CURRENT_W_S
        expanded_q = (query or "").strip()
        if "정보처리기사" in expanded_q:
            expanded_q = "정보처리기사 정보처리"
        elif expanded_q.upper() == "SQL" or "SQL" in expanded_q:
            expanded_q = "SQL 데이터베이스"
        elif "간호" in expanded_q:
            expanded_q = "간호사 간호"
    else:
        w_d, w_s, expanded_q = classify_query_and_expand(query)

    # ----- Dense 채널 -----
    vec_sql = text(
        """
        SELECT qual_id, name
        FROM certificates_vectors
        WHERE embedding IS NOT NULL
          AND (embedding <=> :vec) <= :max_dist
        ORDER BY embedding <=> :vec
        LIMIT :limit
    """
    )
    vec_rows = db.execute(
        vec_sql,
        {"vec": str(query_vec), "max_dist": max_dist, "limit": TOP_PER_QUERY},
    ).fetchall()
    vec_rank_list: list[int] = []
    seen = set()
    for r in vec_rows:
        if r.qual_id not in seen:
            seen.add(r.qual_id)
            vec_rank_list.append(r.qual_id)
    vec_rank_map = {qid: i + 1 for i, qid in enumerate(vec_rank_list)}

    # ----- Sparse 채널: 다중 질의(expanded_q + 원문) RRF 병합 -----
    sparse_map_exp = _sparse_rank_map_for_query(db, expanded_q, TOP_PER_QUERY)
    sparse_map_orig = (
        _sparse_rank_map_for_query(db, query.strip(), TOP_PER_QUERY)
        if query.strip() != expanded_q
        else {}
    )
    all_sparse_qids = set(sparse_map_exp) | set(sparse_map_orig)
    sparse_merged_scores: dict[int, float] = {}
    for qid in all_sparse_qids:
        r1 = sparse_map_exp.get(qid, 9999)
        r2 = sparse_map_orig.get(qid, 9999)
        s1 = 1.0 / (RRF_K_SPARSE_INTERNAL + r1)
        s2 = (
            1.0 / (RRF_K_SPARSE_INTERNAL + r2)
            if sparse_map_orig
            else 0.0
        )
        sparse_merged_scores[qid] = s1 + s2
    sparse_sorted = sorted(
        sparse_merged_scores.keys(),
        key=lambda x: -sparse_merged_scores[x],
    )[:TOP_PER_QUERY]
    text_rank_map = {qid: i + 1 for i, qid in enumerate(sparse_sorted)}

    # ----- 가중치 RRF: Dense + Sparse -----
    all_qids = set(vec_rank_map) | set(text_rank_map)
    rrf_scores: dict[int, float] = {}
    for qid in all_qids:
        rv = vec_rank_map.get(qid, 9999)
        rt = text_rank_map.get(qid, 9999)
        score = w_d * (1.0 / (RRF_K + rv)) + w_s * (1.0 / (RRF_K + rt))
        rrf_scores[qid] = score
    sorted_qids = sorted(rrf_scores.keys(), key=lambda x: -rrf_scores[x])

    # ----- 경량 리랭커: 상위 20건을 쿼리 토큰–name 겹침으로 재정렬 후 top_k -----
    rerank_pool_size = min(20, len(sorted_qids))
    candidates = sorted_qids[:rerank_pool_size]
    query_tokens = [
        t.strip()
        for t in query.split() + expanded_q.split()
        if t.strip()
    ]
    reranked = _keyword_overlap_rerank(db, candidates, query_tokens, top_k)
    return reranked
