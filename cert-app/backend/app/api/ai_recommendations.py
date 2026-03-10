import asyncio
import json
import logging
import os
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text

_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)


def _is_valid_uuid(value: Optional[str]) -> bool:
    return bool(value and _UUID_RE.match(value))

from app.api.deps import get_db_session, check_rate_limit, get_current_user, get_optional_user
from app.utils.ai import get_embedding_async
from app.schemas import (
    SemanticSearchResponse,
    SemanticSearchResultItem,
    HybridRecommendationResponse,
    HybridRecommendationItem,
)
from app.crud import favorite_crud, acquired_cert_crud, get_qualification_aggregated_stats_bulk
from app.redis_client import redis_client

router = APIRouter(prefix="/recommendations/ai", tags=["ai-recommendations"])
logger = logging.getLogger(__name__)

# 하이브리드 RAG 후보 풀 및 정렬 관련 기본 파라미터
HYBRID_TOP_PER_QUERY = 30            # certificates_vectors에서 질의당 가져올 상위 결과 수
HYBRID_GLOBAL_RESULTS_LIMIT = 80     # RRF 이후 전역 후보에서 사용할 상위 결과 수
HYBRID_CANDIDATE_TRIM_LIMIT = 120    # major/semantic 통합 후 유지할 최대 후보 수

# 고도화 RAG( app.rag hybrid_retrieve ) ON/OFF.
# - 기본값: ON (환경변수 미설정 시 True)
# - 비활성화하고 싶을 때만 USE_ENHANCED_RAG=0 / false 로 설정
USE_ENHANCED_RAG = os.environ.get("USE_ENHANCED_RAG", "true").strip().lower() in ("1", "true", "yes")


@router.get("/semantic-search", response_model=SemanticSearchResponse)
async def semantic_search(
    query: str = Query(..., min_length=1, max_length=500, description="Semantic search query"),
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db_session),
    _: None = Depends(check_rate_limit),
    user_id: str = Depends(get_current_user),
) -> SemanticSearchResponse:
    """
    Perform semantic search using pgvector and OpenAI embeddings. 로그인 사용자 전용.
    """
    try:
        query_vector = await get_embedding_async(query)
    except Exception as e:
        logger.exception("semantic_search embedding failed")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="임베딩 서비스를 일시적으로 사용할 수 없습니다.",
        ) from e

    sql = text("""
        SELECT qual_id, qual_name, qual_type, main_field, managing_body,
               1 - (embedding <=> :vec) as similarity
        FROM qualification
        WHERE embedding IS NOT NULL
        ORDER BY embedding <=> :vec
        LIMIT :limit
    """)
    results = db.execute(sql, {"vec": str(query_vector), "limit": limit}).fetchall()
    formatted = [
        SemanticSearchResultItem(
            qual_id=r.qual_id,
            qual_name=r.qual_name,
            qual_type=r.qual_type,
            main_field=r.main_field,
            managing_body=r.managing_body,
            similarity_score=float(r.similarity),
        )
        for r in results
    ]
    return SemanticSearchResponse(query=query, results=formatted)

GUEST_RESULT_LIMIT = 3  # 비로그인 사용자에게 보여줄 최대 결과 수


@router.get("/hybrid-recommendation", response_model=HybridRecommendationResponse)
async def hybrid_recommendation(
    major: str = Query(..., min_length=1, max_length=200, description="User's major"),
    interest: Optional[str] = Query(None, max_length=500, description="Specific interests or career goals"),
    limit: int = Query(5, ge=1, le=20),
    db: Session = Depends(get_db_session),
    _: None = Depends(check_rate_limit),
    user_id: Optional[str] = Depends(get_optional_user),
) -> HybridRecommendationResponse:
    """
    Combines Major-based mapping with Semantic search (Hybrid Search).
    비로그인 사용자도 사용 가능하나 결과를 GUEST_RESULT_LIMIT개로 제한한다.

    2026-02: 사용자 맥락(학년, 프로필 전공, 북마크/취득 자격증 난이도)을 반영해
    추천 난이도를 자동 조절한다.
    """
    # 입력 정제 — 프론트엔드에서 줄바꿈(\n) 등 공백 문자가 붙어올 수 있음
    major = major.strip()
    interest = interest.strip() if interest else None
    interest_provided = bool(interest and interest.strip())
    if not major:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="major는 비어있을 수 없습니다.")

    # --- 0) Redis 캐시 조회 ----------------------------------------------------
    # 전공·관심사·사용자 티어(guest/user) 조합으로 캐시 키를 만들어
    # 동일한 입력에 대해서는 DB/LLM 파이프라인을 재사용해 속도를 높인다.
    user_tier = "guest" if not user_id else "user"
    cache_key = redis_client.make_cache_key(
        "ai:hybrid:v1",
        major=major,
        interest=interest,
        tier=user_tier,
    )
    cached = redis_client.get(cache_key)
    if cached:
        try:
            return HybridRecommendationResponse(**cached)
        except Exception:
            logger.warning("hybrid_recommendation: failed to parse cache for key %s", cache_key)

    # user_id가 UUID 형식이 아닌 경우(예: 구버전 username) 비로그인으로 처리
    if user_id and not _is_valid_uuid(user_id):
        logger.warning("hybrid_recommendation: non-UUID user_id ignored: %r", user_id)
        user_id = None

    # 쿼리 확장 LLM 호출은 제거하고, 전공/관심사를 단순 결합한 텍스트를 사용한다.
    # 이렇게 하면 OpenAI Chat 호출을 없애고 임베딩만 사용해 속도를 크게 개선한다.
    if interest:
        expanded_interest = f"{major} {interest}"
    else:
        expanded_interest = major

    # 처리 시간 측정을 위한 타이머 시작 (메트릭 수집용)
    start_time = time.perf_counter()

    # --- 1) 사용자 맥락 수집 (학년, 프로필 전공, 북마크/취득 자격증 난이도) -----------------
    grade_year: Optional[int] = None
    fav_items, acq_items = [], []

    if user_id:
        profile_row = db.execute(
            text("SELECT detail_major, grade_year FROM profiles WHERE id = :uid"),
            {"uid": user_id},
        ).mappings().first()
        if profile_row and profile_row.get("grade_year") is not None:
            try:
                grade_year = int(profile_row["grade_year"])
            except Exception:
                grade_year = None

        fav_items, _ = favorite_crud.get_by_user(db, user_id, page=1, page_size=100)
        acq_items, _ = acquired_cert_crud.get_by_user(db, user_id, page=1, page_size=200)
    context_qual_ids = list({*(f.qual_id for f in fav_items), *(a.qual_id for a in acq_items)})
    skill_level: Optional[float] = None  # 유저가 이미 소화한 난이도 지표(1~9.9)
    if context_qual_ids:
        stats_map = get_qualification_aggregated_stats_bulk(db, context_qual_ids)
        diffs: List[float] = []
        for qid in context_qual_ids:
            s = stats_map.get(qid) or {}
            if s.get("avg_difficulty") is not None:
                diffs.append(float(s["avg_difficulty"]))
        if diffs:
            # 취득 자격증을 조금 더 크게 반영 (있다면)
            acq_diffs: List[float] = []
            for a in acq_items:
                st = stats_map.get(a.qual_id) or {}
                if st.get("avg_difficulty") is not None:
                    acq_diffs.append(float(st["avg_difficulty"]))
            base = sum(diffs) / len(diffs)
            if acq_diffs:
                base = (base * 0.7) + ((sum(acq_diffs) / len(acq_diffs)) * 0.3)
            skill_level = base

    # 학년·기존 난이도 기반 목표 난이도 영역 설정
    # 기본값: 5.0 (표준)
    target_difficulty = skill_level if skill_level is not None else 5.0
    if grade_year is not None:
        if grade_year <= 2:
            # 1~2학년: 난이도 6 이하 위주로 추천
            if target_difficulty > 6.0:
                target_difficulty = 6.0
        elif grade_year >= 3:
            # 3~4학년 이상: 조금 더 도전적인 난이도
            if target_difficulty < 6.0:
                target_difficulty = 6.0

    # 이미 취득한 자격증은 DB 레벨에서 검색 제외 (Exclusion Logic)
    acq_qual_ids: set[int] = {a.qual_id for a in acq_items}
    exclude_ids_list: List[int] = list(acq_qual_ids) if acq_qual_ids else []

    RRF_K = 60

    def _classify_query_and_expand(q_text: str) -> tuple[float, float, str]:
        """
        질의 타입에 따라 Dense/Sparse 가중치와 풀텍스트용 확장 질의를 결정.
        - w_d: Dense(OpenAI) 가중치
        - w_s: Sparse(키워드) 가중치
        - expanded: 풀텍스트에 사용할 문자열 (간단한 동의어 확장 포함)
        """
        q = (q_text or "").strip()
        base = q
        # 간단한 동의어/키워드 확장 (plainto_tsquery에 들어가므로 공백 구분만 사용)
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
            # 토큰이 명확한 쿼리: Sparse 비중을 조금 더 높인다.
            w_d, w_s = 1.0, 1.2
        else:
            # 설명형/서술형 쿼리: Dense 비중을 높인다.
            w_d, w_s = 1.3, 0.7
        return w_d, w_s, base

    def _hybrid_rrf_from_certificates_vectors(
        db: Session,
        queries: List[str],
        query_vectors: List[List[float]],
        exclude_qual_ids: List[int],
        top_per_query: int = HYBRID_TOP_PER_QUERY,
        use_fulltext: bool = True,
    ) -> tuple[dict[int, float], dict[int, str]]:
        """
        certificates_vectors에서 벡터 검색 + tsvector 풀텍스트 검색을 결합하고
        RRF: Score = w_d/(K+rank_vector) + w_s/(K+rank_text) 로 융합.
        반환: (qual_id -> RRF 점수 합계, qual_id -> qual_name)
        """
        qual_rrf: dict[int, float] = {}
        qual_names: dict[int, str] = {}
        use_github_rrf = os.environ.get("RECOMMENDATION_USE_GITHUB_RRF") == "1"
        for qi, (q_text, q_vec) in enumerate(zip(queries, query_vectors)):
            if use_github_rrf:
                w_d, w_s, expanded_q = 1.0, 1.0, (q_text or "").strip()
            else:
                w_d, w_s, expanded_q = _classify_query_and_expand(q_text)
            # 벡터 검색 (HNSW cosine), 거리 순으로 정렬 후 qual_id별 첫 등장 순위 사용
            vec_sql = text("""
                SELECT qual_id, name, 1 - (embedding <=> :vec) AS similarity
                FROM certificates_vectors
                WHERE embedding IS NOT NULL
                  {exclude}
                ORDER BY embedding <=> :vec
                LIMIT :limit
            """.format(exclude="AND qual_id != ALL(:exclude_ids)" if exclude_qual_ids else ""))
            params_v = {"vec": str(q_vec), "limit": top_per_query}
            if exclude_qual_ids:
                params_v["exclude_ids"] = exclude_qual_ids
            vec_rows = db.execute(vec_sql, params_v).fetchall()
            seen_v: set[int] = set()
            vec_rank_list: List[int] = []
            for r in vec_rows:
                if r.qual_id not in seen_v:
                    seen_v.add(r.qual_id)
                    vec_rank_list.append(r.qual_id)
                    qual_names[r.qual_id] = getattr(r, "name", "") or ""
            vec_rank_map = {qid: i + 1 for i, qid in enumerate(vec_rank_list)}

            text_rank_map: dict[int, int] = {}
            if use_fulltext:
                # 풀텍스트 검색 (content_tsv) — content_tsv 컬럼이 있을 때만
                try:
                    ft_sql = text("""
                        SELECT qual_id, name,
                               ts_rank_cd(content_tsv, plainto_tsquery('simple', :q)) AS rank
                        FROM certificates_vectors
                        WHERE content_tsv @@ plainto_tsquery('simple', :q)
                          {exclude}
                        ORDER BY rank DESC
                        LIMIT :limit
                    """.format(exclude="AND qual_id != ALL(:exclude_ids)" if exclude_qual_ids else ""))
                    params_ft = {"q": expanded_q, "limit": top_per_query}
                    if exclude_qual_ids:
                        params_ft["exclude_ids"] = exclude_qual_ids
                    ft_rows = db.execute(ft_sql, params_ft).fetchall()
                except Exception:
                    db.rollback()
                    ft_rows = []
                seen_t: set[int] = set()
                text_rank_list: List[int] = []
                for r in ft_rows:
                    if r.qual_id not in seen_t:
                        seen_t.add(r.qual_id)
                        text_rank_list.append(r.qual_id)
                        if r.qual_id not in qual_names:
                            qual_names[r.qual_id] = getattr(r, "name", "") or ""
                text_rank_map = {qid: i + 1 for i, qid in enumerate(text_rank_list)}

            # RRF: w_d/(K+rank_vector) + w_s/(K+rank_text) [GitHub는 1/(K+r1)+1/(K+r2)만]
            all_qids = set(vec_rank_map) | set(text_rank_map)
            for qid in all_qids:
                rv = vec_rank_map.get(qid, 9999)
                rt = text_rank_map.get(qid, 9999)
                if use_github_rrf:
                    s = 1.0 / (RRF_K + rv) + 1.0 / (RRF_K + rt)
                else:
                    s = w_d * (1.0 / (RRF_K + rv)) + w_s * (1.0 / (RRF_K + rt))
                    name = qual_names.get(qid, "")
                    if name and q_text and q_text.replace(" ", "") in name.replace(" ", ""):
                        s += 0.05
                qual_rrf[qid] = qual_rrf.get(qid, 0.0) + s

        return qual_rrf, qual_names

    # --- 2) 후보 생성: Major Map + Hybrid RAG (certificates_vectors) --------------------------
    try:
        major_sql = text("""
            SELECT q.qual_id, q.qual_name, q.qual_type, q.main_field,
                   mq.score AS mapping_score, mq.weight AS mapping_weight, mq.reason
            FROM qualification q
            JOIN major_qualification_map mq ON q.qual_id = mq.qual_id
            WHERE mq.major = :major
            ORDER BY mq.score DESC
            LIMIT 60
        """)
        major_results = db.execute(major_sql, {"major": major}).fetchall()

        if not major_results:
            try:
                fuzzy_sql = text("""
                    SELECT DISTINCT ON (q.qual_id)
                           q.qual_id, q.qual_name, q.qual_type, q.main_field,
                           mq.score AS mapping_score,
                           mq.weight AS mapping_weight,
                           mq.reason,
                           similarity(mq.major, :major) AS fuzzy_sim
                    FROM qualification q
                    JOIN major_qualification_map mq ON q.qual_id = mq.qual_id
                    WHERE similarity(mq.major, :major) > 0.35
                    ORDER BY q.qual_id, mq.score DESC
                    LIMIT 60
                """)
                major_results = db.execute(fuzzy_sql, {"major": major}).fetchall()
                if major_results:
                    logger.info("fuzzy major match for %r: found %d certs (trgm fallback)", major, len(major_results))
            except Exception as fuzzy_err:
                logger.warning("fuzzy major search skipped for %r: %s", major, fuzzy_err)
                major_results = []

        use_enhanced_rag_result = False
        global_results = []
        major_sim_lookup = {}

        if USE_ENHANCED_RAG:
            try:
                # 고도화 RAG: BM25 + Vector(dense1536) + Contrastive(768) → 3-way RRF.
                # rag_list 반환 점수 = RRF(BM25, Vector, Contrastive) per chunk → qual_id별 합산.
                from app.rag.retrieve.hybrid import hybrid_retrieve
                rag_list = hybrid_retrieve(
                    db, expanded_interest,
                    top_k=HYBRID_GLOBAL_RESULTS_LIMIT,
                    use_reranker=False,
                )
                hybrid_rrf_scores = {}
                for chunk_id, score in (rag_list or []):
                    part = (chunk_id or "").split(":")
                    if len(part) >= 1 and part[0].isdigit():
                        qid = int(part[0])
                        if qid in acq_qual_ids:
                            continue
                        hybrid_rrf_scores[qid] = hybrid_rrf_scores.get(qid, 0.0) + float(score)
                hybrid_qual_names = {}
                if hybrid_rrf_scores:
                    qual_ids = list(hybrid_rrf_scores.keys())
                    try:
                        name_rows = db.execute(
                            text("SELECT qual_id, qual_name FROM qualification WHERE qual_id = ANY(:ids)"),
                            {"ids": qual_ids},
                        ).fetchall()
                        hybrid_qual_names = {r.qual_id: (r.qual_name or "").strip() for r in name_rows}
                    except Exception:
                        pass
                    for qid in hybrid_rrf_scores:
                        if qid not in hybrid_qual_names:
                            hybrid_qual_names[qid] = ""
                global_results = [
                    type("Row", (), {"qual_id": qid, "qual_name": hybrid_qual_names.get(qid, ""), "similarity": sc})()
                    for qid, sc in sorted(hybrid_rrf_scores.items(), key=lambda x: -x[1])[:HYBRID_GLOBAL_RESULTS_LIMIT]
                ]
                major_vector = await get_embedding_async(major)
                major_sim_sql = text("""
                    SELECT qual_id, MAX(1 - (embedding <=> :vec)) AS major_sim
                    FROM certificates_vectors
                    WHERE embedding IS NOT NULL
                    GROUP BY qual_id
                """)
                m_sims = db.execute(major_sim_sql, {"vec": str(major_vector)}).fetchall()
                major_sim_lookup = {r.qual_id: float(r.major_sim) for r in m_sims}
                use_enhanced_rag_result = True
                logger.info(
                    "hybrid_recommendation: using enhanced RAG, candidates=%d",
                    len(global_results),
                )
            except Exception as e:
                logger.warning(
                    "enhanced RAG failed, falling back to current RAG: %s: %s",
                    type(e).__name__,
                    e,
                    exc_info=True,
                )

        if not use_enhanced_rag_result:
            # 현재 RAG: certificates_vectors 기반 벡터+풀텍스트 RRF
            # Multi-Query Expansion (기존: 3개 유사 질의)
            # 응답 속도와 결과 일관성을 위해, 현재는 확장 질의를 1개만 사용한다.
            multi_queries = [expanded_interest]
            try:
                # 임베딩 2회를 병렬 호출해 지연 절감 (query + major)
                query_vectors, major_vector = await asyncio.gather(
                    asyncio.gather(*[get_embedding_async(q) for q in multi_queries]),
                    get_embedding_async(major),
                )
            except Exception as emb_err:
                logger.exception("hybrid_recommendation embedding failed")
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="임베딩 서비스를 일시적으로 사용할 수 없습니다.",
                ) from emb_err
            hybrid_rrf_scores, hybrid_qual_names = _hybrid_rrf_from_certificates_vectors(
                db,
                multi_queries,
                query_vectors,
                exclude_ids_list,
                top_per_query=HYBRID_TOP_PER_QUERY,
                use_fulltext=interest_provided,
            )
            global_results = [
                type("Row", (), {"qual_id": qid, "qual_name": hybrid_qual_names.get(qid, ""), "similarity": sc})()
                for qid, sc in sorted(hybrid_rrf_scores.items(), key=lambda x: -x[1])[:HYBRID_GLOBAL_RESULTS_LIMIT]
            ]
            logger.debug(
                "hybrid_recommendation.pool major=%r interest_provided=%r "
                "top_per_query=%d hybrid_candidates=%d global_results=%d",
                major,
                interest_provided,
                HYBRID_TOP_PER_QUERY,
                len(hybrid_rrf_scores),
                len(global_results),
            )
            major_sim_sql = text("""
                SELECT qual_id, MAX(1 - (embedding <=> :vec)) AS major_sim
                FROM certificates_vectors
                WHERE embedding IS NOT NULL
                GROUP BY qual_id
            """)
            try:
                m_sims = db.execute(major_sim_sql, {"vec": str(major_vector)}).fetchall()
                major_sim_lookup = {r.qual_id: float(r.major_sim) for r in m_sims}
            except Exception:
                major_sim_lookup = {}
    except Exception as e:
        logger.exception("hybrid_recommendation DB query failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="추천 데이터 조회 중 오류가 발생했습니다.",
        ) from e

    # --- 3) 후보 통합 -------------------------------------------------------
    candidate_map: dict[int, dict] = {}

    for r in major_results:
        if r.qual_id in acq_qual_ids:
            continue
        m_sim = major_sim_lookup.get(r.qual_id, 0.5)
        # mapping_weight 가 있으면 score 보정에 반영 (기본 1.0)
        w = float(r.mapping_weight or 1.0)
        base_major_score = max(float(r.mapping_score or 0) * min(w, 1.5), m_sim * 10.0)
        candidate_map[r.qual_id] = {
            "qual_id": r.qual_id,
            "qual_name": r.qual_name,
            "major_score": base_major_score,
            "reason": r.reason or "전공 맞춤형 자격증",
            "semantic_similarity": 0.0,
        }

    for r in global_results:
        if r.qual_id in acq_qual_ids:
            continue
        m_sim = major_sim_lookup.get(r.qual_id, 0.3)
        if r.qual_id in candidate_map:
            candidate_map[r.qual_id]["semantic_similarity"] = float(r.similarity)
        else:
            candidate_map[r.qual_id] = {
                "qual_id": r.qual_id,
                "qual_name": r.qual_name,
                "major_score": m_sim * 10.0,
                "reason": "관심사 기반 연관 자격증",
                "semantic_similarity": float(r.similarity),
            }

    # 후보 수가 너무 많을 경우(이론상 수백 개) 이후 단계 속도를 위해 상위 일부만 남긴다.
    initial_candidate_count = len(candidate_map)
    if len(candidate_map) > HYBRID_CANDIDATE_TRIM_LIMIT:
        trimmed = sorted(
            candidate_map.values(),
            key=lambda c: (c["major_score"] * 0.6) + (c["semantic_similarity"] * 0.4),
            reverse=True,
        )[:HYBRID_CANDIDATE_TRIM_LIMIT]
        candidate_map = {c["qual_id"]: c for c in trimmed}

    logger.debug(
        "hybrid_recommendation.candidates major=%r initial=%d after_trim=%d",
        major,
        initial_candidate_count,
        len(candidate_map),
    )

    # --- 4) 난이도 + 합격률 통계 일괄 로드 ------------------------------------
    candidate_ids = list(candidate_map.keys())
    diff_lookup: dict[int, Optional[float]] = {}
    pass_rate_lookup: dict[int, Optional[float]] = {}

    if candidate_ids:
        stats = get_qualification_aggregated_stats_bulk(db, candidate_ids)
        for qid in candidate_ids:
            s = stats.get(qid) or {}
            diff_lookup[qid] = s.get("avg_difficulty")
            pass_rate_lookup[qid] = s.get("latest_pass_rate")

    # --- 5) RRF (Reciprocal Rank Fusion) 점수 계산 ---------------------------
    # 세 가지 순위 리스트를 RRF로 융합: major_score / semantic_similarity / major_sim
    n = len(candidate_map)

    # 시멘틱 유사도는 RRF에 들어가기 전에 단순 max-normalization으로 0~1 스케일로 맞춘다.
    if candidate_map:
        max_sem_raw = max(c["semantic_similarity"] for c in candidate_map.values())
        if max_sem_raw > 0:
            for c in candidate_map.values():
                c["semantic_similarity"] = float(c["semantic_similarity"]) / max_sem_raw

    major_ranked = sorted(candidate_map.keys(), key=lambda c: candidate_map[c]["major_score"], reverse=True)
    semantic_ranked = sorted(candidate_map.keys(), key=lambda c: candidate_map[c]["semantic_similarity"], reverse=True)
    major_sim_ranked = sorted(candidate_map.keys(), key=lambda c: major_sim_lookup.get(c, 0.0), reverse=True)

    major_rank_map = {cid: i + 1 for i, cid in enumerate(major_ranked)}
    semantic_rank_map = {cid: i + 1 for i, cid in enumerate(semantic_ranked)}
    major_sim_rank_map = {cid: i + 1 for i, cid in enumerate(major_sim_ranked)}

    # interest 있으면 semantic 가중치 높임 (2배), 없으면 균등
    w_sem = 2.0 if interest_provided else 1.0
    w_maj = 1.0
    w_msim = 1.0

    for cid, c in candidate_map.items():
        rrf = (
            w_maj  / (RRF_K + major_rank_map.get(cid, n + 1)) +
            w_sem  / (RRF_K + semantic_rank_map.get(cid, n + 1)) +
            w_msim / (RRF_K + major_sim_rank_map.get(cid, n + 1))
        )
        c["rrf_score"] = rrf

    # --- 6) 합격률 시그널 계산 ------------------------------------------------
    # 적정 합격률(25~55%) 구간에 점수 부스트, 너무 낮거나(< 5%) 너무 높으면(> 85%) 약간 감점
    # 추가로, 매우 낮은 합격률(< 20%) 시험은 체감 난이도가 높다고 보고 가중치를 더 준다.
    def _pass_rate_factor(pr: Optional[float]) -> float:
        if pr is None:
            return 1.0  # 데이터 없으면 중립
        p = pr / 100.0
        base = max(0.85, 1.05 - abs(p - 0.40) * 0.5)
        if p < 0.20:
            base *= 1.15
        elif p < 0.40:
            base *= 1.05
        elif p > 0.70:
            base *= 0.90
        return base

    # --- 7) 최종 스코어 (정규화 + 가중합) --------------------------------------
    # major_score와 semantic_similarity를 0~1 범위로 정규화한 뒤
    # 가중치를 두어 Hybrid Score를 계산하고, 여기에 난이도·합격률 보정을 곱한다.
    final_results: list[dict] = []

    # major_score 정규화용 min/max
    if candidate_map:
        max_major = max(c["major_score"] for c in candidate_map.values())
        min_major = min(c["major_score"] for c in candidate_map.values())
        major_span = max_major - min_major
    else:
        max_major = min_major = major_span = 0.0

    for cid, c in candidate_map.items():
        diff = diff_lookup.get(cid)
        difficulty_factor = 1.0
        if diff is not None:
            if grade_year is not None and grade_year >= 3 and diff < 3.0:
                difficulty_factor *= 0.80
            delta = abs(diff - target_difficulty)
            # 목표 난이도에서 멀어질수록 조금 더 강하게 페널티를 주어
            # 체감 난이도와 맞지 않는 추천이 상위에 오는 것을 줄인다.
            difficulty_factor *= max(0.70, 1.15 - (delta / 3.0))

        pr_factor = _pass_rate_factor(pass_rate_lookup.get(cid))

        # 0~1 범위로 정규화된 major / semantic (UI 전공 연관성·관심도 일치 바용). 표시가 100% 초과하지 않도록 엄격히 클램핑.
        if major_span > 0:
            major_norm = (c["major_score"] - min_major) / major_span
        else:
            major_norm = 1.0
        major_norm = max(0.0, min(1.0, major_norm))
        sem_norm = max(0.0, min(1.0, float(c["semantic_similarity"])))
        c["major_score_normalized"] = major_norm
        c["semantic_score_normalized"] = sem_norm

        # 정합성 기본 점수: interest가 있을 때는 관심사(semantic)를 더 강하게 반영
        if interest_provided:
            base_match = 0.3 * major_norm + 0.7 * sem_norm
        else:
            base_match = 0.5 * major_norm + 0.5 * sem_norm
        base_match = max(0.0, min(1.0, base_match))

        # 최종 하이브리드 = (전공/관심사 매칭) × 난이도 보정 × 합격률 보정. 보정 곱이 1 초과할 수 있으므로 반드시 0~1 클램핑.
        h_score = base_match * difficulty_factor * pr_factor
        c["hybrid_score"] = max(0.0, min(1.0, h_score))
        c["pass_rate"] = pass_rate_lookup.get(cid)
        final_results.append(c)

    # --- 7-1) 관심도 레벨(1~9) 산출 -------------------------------------------
    # hybrid_score(절대 0~1) 기반 비선형 매핑. 정합성은 재정규화하지 않음.
    max_h = min_h = 0.0
    if final_results:
        max_h = max(c["hybrid_score"] for c in final_results)
        min_h = min(c["hybrid_score"] for c in final_results)
        ranked_for_interest = sorted(final_results, key=lambda x: x["hybrid_score"], reverse=True)
        n_rank = len(ranked_for_interest)
        if n_rank == 1:
            ranked_for_interest[0]["interest_level"] = 9
        elif n_rank > 1:
            for c in ranked_for_interest:
                frac = max(0.0, min(c["hybrid_score"], 1.0))
                shaped = frac ** 0.7
                level = 1 + int(round(shaped * 8))
                c["interest_level"] = max(1, min(level, 9))

    # --- 8) 1차 정렬 & 결과 수 제한 ------------------------------------------
    effective_limit = min(limit, GUEST_RESULT_LIMIT) if not user_id else limit

    # final_results가 비어 있는 경우 방어적 폴백:
    # - major_qualification_map 기반 상위 자격증들로 최소한 몇 개는 내려준다.
    if not final_results and major_results:
        logger.info(
            "hybrid_recommendation: final_results empty; using major_results fallback. "
            "major=%r, interest_provided=%r, major_rows=%d",
            major,
            interest_provided,
            len(major_results),
        )
        fallback = []
        for r in major_results[:effective_limit]:
            raw = float(r.mapping_score or 0.0)
            fallback.append(
                {
                    "qual_id": r.qual_id,
                    "qual_name": r.qual_name,
                    "major_score": raw,
                    "reason": r.reason or f"전공({major})과의 연관성이 높은 자격증입니다.",
                    "semantic_similarity": 0.0,
                    "hybrid_score": max(0.0, min(1.0, raw)),
                    "pass_rate": None,
                    "rrf_score": None,
                    "interest_level": None,
                }
            )
        final_results = fallback

    # LLM re-ranking 후보로 최대 20개를 준비 (로그인 사용자) / 게스트는 그대로 잘라냄
    rrf_sorted = sorted(final_results, key=lambda x: x["hybrid_score"], reverse=True)
    rerank_pool = rrf_sorted[:20] if user_id else rrf_sorted[:effective_limit]
    sorted_results = rerank_pool[:effective_limit]  # 기본값 (폴백용)

    # --- 9) 규칙 기반 reason 생성 --------------------------
    def _fallback_reason(c: dict, diff: Optional[float]) -> str:
        ms, ss = c["major_score"], c["semantic_similarity"]
        pr = pass_rate_lookup.get(c["qual_id"]) if "qual_id" in c else None

        # 난이도 문구에 사용할 표시용 난이도 (실제 로직에는 영향 X)
        display_diff = diff
        if diff is not None and grade_year is not None and grade_year >= 4:
            # 4학년 이상에게는 5.0~7.0 구간을 적합 난이도로 강조
            display_diff = max(5.0, min(diff, 7.0))

        # 전공/관심사·난이도·합격률 조합에 따른 기본 설명 패턴
        if ms > 8.0 and ss > 0.6:
            base = f"전공({major})과 매우 밀접하며 입력하신 관심사와도 강하게 연결되는 핵심 자격증입니다."
        elif ms > 8.0:
            base = "전공 분야의 핵심 역량을 증명할 수 있는 대표적인 자격증입니다."
        elif ss > 0.7 and interest:
            # interest는 클라이언트에서 받은 값 그대로 사용 (연어/언어 등 표기 확인용)
            base = f"입력하신 \"{interest}\"와(과) 내용이 밀접하게 연결된 실무 중심 자격증입니다."
        elif ss > 0.5 and interest:
            base = f"관심사와 연관된 업무에서 자주 활용되는 자격증입니다."
        elif diff is not None and diff > target_difficulty + 1.5:
            base = "현재 수준보다 한 단계 높은 난이도로, 성장과 포트폴리오 강화를 노릴 때 적합한 자격증입니다."
        else:
            base = c.get("reason") or "전공·관심사 분석에 기반해 선별된 추천 자격증입니다."

        # 합격률 맥락 추가
        if pr is not None:
            if pr < 20:
                base += " 합격률이 낮아 난이도는 높은 편이지만, 취득 시 경쟁력이 크게 올라갑니다."
            elif pr < 40:
                base += " 합격률이 높지는 않지만 준비할 가치가 큰 자격증입니다."
            elif pr > 70:
                base += " 비교적 합격률이 높아 입문·기초를 다지기 좋은 자격증입니다."

        # 난이도 맥락 추가 (표시용 난이도 사용)
        if display_diff is not None and grade_year is not None:
            if grade_year <= 2 and display_diff <= 6.0:
                base += f" 현재 {grade_year}학년 수준에서 도전하기 좋은 난이도({display_diff:.1f})입니다."
            elif grade_year >= 3:
                base += f" {grade_year}학년에게 적합한 난이도({display_diff:.1f})로 설계되어 있습니다."

        return base

    items = []
    for c in sorted_results:
        reason = _fallback_reason(c, diff_lookup.get(c["qual_id"]))
        items.append(
            HybridRecommendationItem(
                qual_id=c["qual_id"],
                qual_name=c["qual_name"],
                major_score=c["major_score"],
                reason=reason,
                semantic_similarity=c["semantic_similarity"],
                hybrid_score=c["hybrid_score"],
                pass_rate=c.get("pass_rate"),
                rrf_score=c.get("rrf_score"),
                llm_reason=False,
                major_score_normalized=c.get("major_score_normalized"),
                semantic_score_normalized=c.get("semantic_score_normalized"),
            )
        )

    response = HybridRecommendationResponse(
        mode="hybrid",
        major=major,
        interest=interest,
        results=items,
        guest_limited=not bool(user_id),
        rag_mode="enhanced" if use_enhanced_rag_result else "current",
        retrieval_pipeline="bm25_vector_contrastive_rrf" if use_enhanced_rag_result else "vector_fulltext_rrf",
    )

    # 메트릭 로깅: 처리 시간, 후보 수, 점수 분포 등 (개인정보 제외)
    elapsed_ms = (time.perf_counter() - start_time) * 1000.0
    logger.info(
        "hybrid_recommendation.metrics major=%r interest_len=%d tier=%s "
        "candidates=%d final=%d elapsed_ms=%.1f max_h=%.3f min_h=%.3f",
        major,
        len(interest) if interest else 0,
        "guest" if not user_id else "user",
        len(candidate_map),
        len(final_results),
        elapsed_ms,
        max_h,
        min_h,
    )

    # --- 12) Redis 캐시에 최종 결과 저장 ---------------------------------------
    try:
        redis_client.set(cache_key, response.model_dump(mode="json"), ttl=3600)
    except Exception:
        logger.warning("hybrid_recommendation: failed to write cache for key %s", cache_key)

    return response


def _rag_eval_metrics_path() -> Path:
    """backend/data/rag_eval_metrics_8.json 경로 (실행 CWD가 backend일 때)."""
    base = Path(__file__).resolve().parent.parent.parent
    return base / "data" / "rag_eval_metrics_8.json"


@router.get("/rag-eval-metrics")
async def get_rag_eval_metrics() -> Dict[str, Any]:
    """
    골든 8개 기준 RAG 평가 메트릭. 베이스라인 대비 MRR, Recall@5, Recall@10 및 향상률.
    데이터: data/rag_eval_metrics_8.json (eval 실행 후 스크립트로 갱신).
    """
    path = _rag_eval_metrics_path()
    if not path.is_file():
        return {"golden_n": 8, "baseline": {}, "enhanced_reranker": {}, "pct_vs_baseline": {}}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        logger.warning("rag_eval_metrics read failed: %s", e)
        return {"golden_n": 8, "baseline": {}, "enhanced_reranker": {}, "pct_vs_baseline": {}}
    return data
