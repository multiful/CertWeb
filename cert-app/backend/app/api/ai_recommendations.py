import asyncio
import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.api.deps import get_db_session, check_rate_limit, get_current_user, get_optional_user
from app.utils.ai import get_embedding_async
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
    try:
        interest_vector, major_vector = await asyncio.gather(
            get_embedding_async(interest or major),
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

    # --- 2) 기존 Hybrid 후보 생성 로직 ----------------------------------------------
    try:
        major_sql = text("""
            SELECT q.qual_id, q.qual_name, q.qual_type, q.main_field, mq.score as mapping_score, mq.reason
            FROM qualification q
            JOIN major_qualification_map mq ON q.qual_id = mq.qual_id
            WHERE mq.major = :major
            ORDER BY mq.score DESC
            LIMIT 50
        """)
        major_results = db.execute(major_sql, {"major": major}).fetchall()
        global_semantic_sql = text("""
            SELECT qual_id, qual_name,
                   1 - (embedding <=> :vec) as similarity
            FROM qualification
            WHERE embedding IS NOT NULL
            ORDER BY embedding <=> :vec
            LIMIT 100
        """)
        global_results = db.execute(global_semantic_sql, {"vec": str(interest_vector)}).fetchall()

        major_sim_sql = text("""
            SELECT qual_id, 1 - (embedding <=> :vec) as major_sim
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

    # 3) Combine Candidates
    candidate_map = {}
    
    # Process major results from map
    for r in major_results:
        # Scale DB score (0-10) to 0.5-1.0 base if it exists, 
        # but also consider semantic similarity to major name
        m_sim = major_sim_lookup.get(r.qual_id, 0.5)
        # Use existing score if high, otherwise fallback to semantic
        base_major_score = max(float(r.mapping_score or 0), m_sim * 10.0)
        
        candidate_map[r.qual_id] = {
            "qual_id": r.qual_id,
            "qual_name": r.qual_name,
            "major_score": base_major_score,
            "reason": r.reason or "전공 맞춤형 자격증",
            "semantic_similarity": 0.0 
        }

    # Process interest results
    for r in global_results:
        m_sim = major_sim_lookup.get(r.qual_id, 0.3)
        if r.qual_id in candidate_map:
            candidate_map[r.qual_id]["semantic_similarity"] = float(r.similarity)
        else:
            # New candidate from interest
            candidate_map[r.qual_id] = {
                "qual_id": r.qual_id,
                "qual_name": r.qual_name,
                "major_score": m_sim * 10.0, # Purely semantic fallback
                "reason": "관심사 기반 연관 자격증",
                "semantic_similarity": float(r.similarity)
            }

    # --- 3) 난이도 정보 결합 ----------------------------------------------
    # 후보들의 난이도를 한 번에 가져와 필터링/가중치에 사용
    candidate_ids = list(candidate_map.keys())
    diff_lookup: dict[int, Optional[float]] = {}
    if candidate_ids:
        diff_stats = get_qualification_aggregated_stats_bulk(db, candidate_ids)
        for qid in candidate_ids:
            s = diff_stats.get(qid) or {}
            diff_lookup[qid] = s.get("avg_difficulty")

    # --- 4) Final Hybrid Scoring & Thresholding (난이도 반영) -----------------------
    final_results = []
    for cid, c in candidate_map.items():
        # Minimum relevance: must have some major link OR high interest similarity
        if c["major_score"] < 4.0 and c["semantic_similarity"] < 0.25:
            continue

        # 난이도 기반 가중치
        diff = diff_lookup.get(cid)
        difficulty_factor = 1.0
        if diff is not None:
            # 학년별 하드 필터: 1~2학년에게는 지나치게 높은 난이도는 제외
            if grade_year is not None and grade_year <= 2 and diff > 8.0:
                continue
            # 3~4학년 이상인데 너무 쉬운(<=3) 자격증은 우선순위 낮춤
            if grade_year is not None and grade_year >= 3 and diff < 3.0:
                difficulty_factor *= 0.8

            # 타깃 난이도와의 거리로 미세 가중치 (±4 범위 안이면 거의 1.0 유지)
            delta = abs(diff - target_difficulty)
            difficulty_factor *= max(0.75, 1.1 - (delta / 4.0))

        # Hybrid Score = 0.6 * Interest + 0.4 * Major, 이후 난이도 가중치 적용
        h_score = (c["semantic_similarity"] * 0.6) + (c["major_score"] / 10.0 * 0.4)
        h_score *= difficulty_factor
        c["hybrid_score"] = h_score
        
        # Format reason more nicely
        if c["major_score"] > 8.0 and c["semantic_similarity"] > 0.4:
            c["reason"] = f"전공({major})과 매우 밀접하며, 관심사({interest or '입력'})와도 높은 연관성을 보입니다."
        elif c["major_score"] > 7.0:
            c["reason"] = f"전공 분야의 핵심 역량을 증명할 수 있는 주요 자격증입니다."
        elif c["semantic_similarity"] > 0.5:
            c["reason"] = f"작성해주신 관심사({interest or '입력'}) 분야에서 매우 인기 있는 전문 자격증입니다."

        # 난이도·학년 기반 보정 설명 추가
        if diff is not None:
            if grade_year is not None:
                if grade_year <= 2 and diff <= 6.0:
                    c["reason"] += f" 현재 {grade_year}학년 수준에서 무리 없이 도전할 수 있는 난이도({diff:.1f})로 판단되었습니다."
                elif grade_year >= 3 and diff >= 6.0:
                    c["reason"] += f" {grade_year}학년 및 이미 취득/북마크한 자격증 난이도를 고려해 한 단계 높은 난이도({diff:.1f})를 추천합니다."
            elif skill_level is not None:
                if diff >= skill_level + 1.0:
                    c["reason"] += f" 이미 학습하신 자격증들의 평균 난이도({skill_level:.1f})보다 약간 높은 레벨({diff:.1f})로 성장에 도움이 됩니다."
            
        final_results.append(c)

    # 비로그인 사용자는 GUEST_RESULT_LIMIT개로 제한
    effective_limit = min(limit, GUEST_RESULT_LIMIT) if not user_id else limit
    sorted_results = sorted(final_results, key=lambda x: x["hybrid_score"], reverse=True)[:effective_limit]
    items = [
        HybridRecommendationItem(
            qual_id=c["qual_id"],
            qual_name=c["qual_name"],
            major_score=c["major_score"],
            reason=c["reason"],
            semantic_similarity=c["semantic_similarity"],
            hybrid_score=c["hybrid_score"],
        )
        for c in sorted_results
    ]
    return HybridRecommendationResponse(
        mode="hybrid",
        major=major,
        interest=interest,
        results=items,
        guest_limited=not bool(user_id),
    )
