import asyncio
import logging
import re
from typing import List, Optional

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
from app.utils.ai import get_embedding_async, generate_reasons_batch, expand_query_async, llm_rerank_and_reason
from app.schemas import (
    SemanticSearchResponse,
    SemanticSearchResultItem,
    HybridRecommendationResponse,
    HybridRecommendationItem,
)
from app.crud import favorite_crud, acquired_cert_crud, get_qualification_aggregated_stats_bulk

router = APIRouter(prefix="/recommendations/ai", tags=["ai-recommendations"])
logger = logging.getLogger(__name__)


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
    if not major:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="major는 비어있을 수 없습니다.")

    # user_id가 UUID 형식이 아닌 경우(예: 구버전 username) 비로그인으로 처리
    if user_id and not _is_valid_uuid(user_id):
        logger.warning("hybrid_recommendation: non-UUID user_id ignored: %r", user_id)
        user_id = None

    try:
        # Query Expansion: 관심사를 임베딩 전에 풍부한 키워드로 확장 (HyDE-style)
        # expand_query_async 실패 시 원본 텍스트 그대로 사용
        expanded_interest = await expand_query_async(major, interest)
        interest_vector, major_vector = await asyncio.gather(
            get_embedding_async(expanded_interest),
            get_embedding_async(major),
        )
    except Exception as e:
        logger.exception("hybrid_recommendation embedding failed")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="임베딩 서비스를 일시적으로 사용할 수 없습니다.",
        ) from e

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

    # --- 2) 후보 생성: Major Map + Semantic Search (병렬) --------------------------
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

        # --- Fuzzy Major Matching 폴백 -----------------------------------
        # 입력 전공이 major_qualification_map에 없을 경우 pg_trgm 유사도로 가장 근접한
        # 전공을 찾아 그 전공의 자격증 매핑을 활용한다 (커버리지 대폭 향상).
        if not major_results:
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
                logger.info(
                    "fuzzy major match for %r: found %d certs (trgm fallback)",
                    major, len(major_results),
                )

        # 관심사 기반 semantic search (TOP-120)
        global_semantic_sql = text("""
            SELECT qual_id, qual_name,
                   1 - (embedding <=> :vec) AS similarity
            FROM qualification
            WHERE embedding IS NOT NULL
            ORDER BY embedding <=> :vec
            LIMIT 120
        """)
        global_results = db.execute(global_semantic_sql, {"vec": str(interest_vector)}).fetchall()

        # 전공명 자체의 벡터 유사도 (모든 후보 대상)
        major_sim_sql = text("""
            SELECT qual_id, 1 - (embedding <=> :vec) AS major_sim
            FROM qualification
            WHERE embedding IS NOT NULL
        """)
        m_sims = db.execute(major_sim_sql, {"vec": str(major_vector)}).fetchall()
        major_sim_lookup = {r.qual_id: float(r.major_sim) for r in m_sims}
    except Exception as e:
        logger.exception("hybrid_recommendation DB query failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="추천 데이터 조회 중 오류가 발생했습니다.",
        ) from e

    # --- 3) 후보 통합 -------------------------------------------------------
    # 이미 취득한 자격증은 추천에서 제외 (acq_items은 위에서 이미 로드됨)
    acq_qual_ids: set[int] = {a.qual_id for a in acq_items}

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
    RRF_K = 60
    n = len(candidate_map)

    major_ranked = sorted(candidate_map.keys(), key=lambda c: candidate_map[c]["major_score"], reverse=True)
    semantic_ranked = sorted(candidate_map.keys(), key=lambda c: candidate_map[c]["semantic_similarity"], reverse=True)
    major_sim_ranked = sorted(candidate_map.keys(), key=lambda c: major_sim_lookup.get(c, 0.0), reverse=True)

    major_rank_map = {cid: i + 1 for i, cid in enumerate(major_ranked)}
    semantic_rank_map = {cid: i + 1 for i, cid in enumerate(semantic_ranked)}
    major_sim_rank_map = {cid: i + 1 for i, cid in enumerate(major_sim_ranked)}

    interest_provided = bool(interest and interest.strip())
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
    def _pass_rate_factor(pr: Optional[float]) -> float:
        if pr is None:
            return 1.0  # 데이터 없으면 중립
        p = pr / 100.0
        # 벨 곡선 중심 0.40, 최솟값 0.85 (감점 최대 15%)
        return max(0.85, 1.05 - abs(p - 0.40) * 0.5)

    # --- 7) 최종 스코어 & 필터링 ---------------------------------------------
    min_semantic = 0.15 if interest_provided else 0.0
    final_results: list[dict] = []

    for cid, c in candidate_map.items():
        if interest_provided and c["semantic_similarity"] < min_semantic:
            continue
        if c["major_score"] < 3.0 and c["semantic_similarity"] < 0.20:
            continue

        diff = diff_lookup.get(cid)
        difficulty_factor = 1.0
        if diff is not None:
            if grade_year is not None and grade_year <= 2 and diff > 8.0:
                continue
            if grade_year is not None and grade_year >= 3 and diff < 3.0:
                difficulty_factor *= 0.80
            delta = abs(diff - target_difficulty)
            difficulty_factor *= max(0.75, 1.1 - (delta / 4.0))

        pr_factor = _pass_rate_factor(pass_rate_lookup.get(cid))

        # 최종 하이브리드 = RRF × 난이도 보정 × 합격률 보정 (정규화용으로 10배)
        h_score = c["rrf_score"] * difficulty_factor * pr_factor * 10.0
        c["hybrid_score"] = h_score
        c["pass_rate"] = pass_rate_lookup.get(cid)
        final_results.append(c)

    # --- 8) 1차 정렬 & 결과 수 제한 ------------------------------------------
    effective_limit = min(limit, GUEST_RESULT_LIMIT) if not user_id else limit
    # LLM re-ranking 후보로 최대 20개를 준비 (로그인 사용자) / 게스트는 그대로 잘라냄
    rrf_sorted = sorted(final_results, key=lambda x: x["hybrid_score"], reverse=True)
    rerank_pool = rrf_sorted[:20] if user_id else rrf_sorted[:effective_limit]
    sorted_results = rerank_pool[:effective_limit]  # 기본값 (폴백용)

    # --- 9) LLM Cross-encoder Re-ranking + 이유 생성 -------------------------
    # 로그인 사용자 전용: GPT-4o-mini가 RRF top-20을 사용자 맥락에 맞게 재정렬하고
    # 이유를 동시에 생성한다. 실패 시 기존 RRF 순서 + generate_reasons_batch로 폴백.
    llm_reasons: List[str] = []
    reranked = False

    if user_id and rerank_pool:
        rerank_input = [
            {
                "qual_id": c["qual_id"],
                "qual_name": c["qual_name"],
                "pass_rate": c.get("pass_rate"),
            }
            for c in rerank_pool
        ]
        rerank_result = await llm_rerank_and_reason(
            major=major,
            interest=interest,
            candidates=rerank_input,
            top_n=effective_limit,
            grade_year=grade_year,
            skill_level=skill_level,
        )
        if rerank_result:
            qual_id_to_c = {c["qual_id"]: c for c in rerank_pool}
            new_order = [qual_id_to_c[r["qual_id"]] for r in rerank_result if r["qual_id"] in qual_id_to_c]
            if len(new_order) >= effective_limit:
                sorted_results = new_order[:effective_limit]
                llm_reasons = [r["reason"] for r in rerank_result[:effective_limit]]
                reranked = True
                logger.info("llm_rerank applied: %d items reranked for major=%r", len(sorted_results), major)

    # LLM re-ranking 실패 시 기존 generate_reasons_batch로 폴백
    if user_id and not reranked and sorted_results:
        llm_input = [{"qual_name": c["qual_name"], "pass_rate": c.get("pass_rate")} for c in sorted_results]
        llm_reasons = await generate_reasons_batch(
            major=major,
            interest=interest,
            candidates=llm_input,
            grade_year=grade_year,
            skill_level=skill_level,
        )

    # --- 10) 폴백 reason (LLM 실패 시 또는 비로그인) --------------------------
    def _fallback_reason(c: dict, diff: Optional[float]) -> str:
        ms, ss = c["major_score"], c["semantic_similarity"]
        if ms > 8.0 and ss > 0.4:
            base = f"전공({major})과 매우 밀접하며 관심사와도 높은 연관성을 보입니다."
        elif ms > 7.0:
            base = "전공 분야의 핵심 역량을 증명할 수 있는 주요 자격증입니다."
        elif ss > 0.5:
            base = f"작성하신 관심사 분야에서 매우 인기 있는 전문 자격증입니다."
        else:
            base = c.get("reason") or "전공·관심사 분석에 기반한 추천 자격증입니다."
        if diff is not None and grade_year is not None:
            if grade_year <= 2 and diff <= 6.0:
                base += f" 현재 {grade_year}학년 수준에서 도전하기 좋은 난이도({diff:.1f})입니다."
            elif grade_year >= 3 and diff >= 6.0:
                base += f" {grade_year}학년에게 적합한 난이도({diff:.1f})입니다."
        return base

    items = []
    for i, c in enumerate(sorted_results):
        use_llm = bool(llm_reasons) and i < len(llm_reasons) and llm_reasons[i]
        reason = llm_reasons[i] if use_llm else _fallback_reason(c, diff_lookup.get(c["qual_id"]))
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
                llm_reason=use_llm,
            )
        )

    return HybridRecommendationResponse(
        mode="hybrid",
        major=major,
        interest=interest,
        results=items,
        guest_limited=not bool(user_id),
    )
