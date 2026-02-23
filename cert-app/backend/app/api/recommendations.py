"""Recommendation API routes."""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import text, or_
import logging

from app.api.deps import get_db_session, check_rate_limit, get_current_user, get_optional_user
from app.schemas import (
    RecommendationListResponse,
    RecommendationResponse,
    JobCertificationRecommendationResponse,
    RelatedJobResponse,
    AvailableMajorsResponse
)
from app.crud import major_map_crud, stats_crud
from app.redis_client import redis_client
from app.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


def get_cache_ttl() -> int:
    """Get cache TTL for recommendations."""
    return settings.CACHE_TTL_RECOMMENDATIONS


def generate_recommendation_reason(
    mapping,
    latest_stats: Optional[object]
) -> str:
    """Generate recommendation reason text."""
    reasons = []
    
    # Use stored reason if available
    if mapping.reason:
        return mapping.reason
    
    # Generate based on data
    if mapping.score >= 8:
        reasons.append("전공과 높은 연관성")
    elif mapping.score >= 5:
        reasons.append("전공과 관련된 분야")
    else:
        reasons.append("보조적 자격증")
    
    if latest_stats:
        if latest_stats.pass_rate and latest_stats.pass_rate >= 70:
            reasons.append(f"합격률 {latest_stats.pass_rate:.1f}%로 안정적")
        elif latest_stats.pass_rate and latest_stats.pass_rate <= 30:
            reasons.append(f"경쟁률 높음 (합격률 {latest_stats.pass_rate:.1f}%)")
        
        if latest_stats.difficulty_score:
            if latest_stats.difficulty_score >= 7:
                reasons.append("고난이도 시험")
            elif latest_stats.difficulty_score <= 4:
                reasons.append("입문자에게 적합")
    
    return " / ".join(reasons) if reasons else "전공 기반 추천"


@router.get(
    "",
    response_model=RecommendationListResponse,
    summary="Get recommendations by major",
    description="Get certification recommendations based on major/field of study."
)
async def get_recommendations(
    major: str = Query(..., description="Major or field of study"),
    limit: int = Query(10, ge=1, le=50, description="Number of recommendations"),
    db: Session = Depends(get_db_session),
    _: None = Depends(check_rate_limit)
):
    """Get certification recommendations for a major."""
    cache_key = redis_client.make_cache_key(
        "recs:v5",
        major=major.lower().strip(),
        limit=limit
    )
    
    # Try cache
    try:
        cached = redis_client.get(cache_key)
        if cached and isinstance(cached, dict):
            logger.debug(f"Cache hit for recommendations: {major}")
            return RecommendationListResponse(**cached)
    except Exception as e:
        logger.warning(f"Cache read failed for recommendations: {e}")
    
    # Get mappings from database
    search_major = major.strip()
    mappings = major_map_crud.get_by_major_with_stats(db, search_major, limit)
    
    # 1. If no exact match, try stripping "학부", "학과", "공학부" and fuzzy matching
    if not mappings:
        # Clean major name to find core keyword
        clean_major = search_major
        for suffix in ["학부", "학과", "전공", "공학부"]:
            if clean_major.endswith(suffix):
                clean_major = clean_major[:-len(suffix)]
                break
        
        from app.models import MajorQualificationMap
        # Find the first major in MajorQualificationMap that contains or is contained by the clean name
        matched_map = db.query(MajorQualificationMap.major).filter(
            or_(
                MajorQualificationMap.major.ilike(f"%{clean_major}%"),
                text(f"'{search_major}' ILIKE '%' || major || '%'")
            )
        ).first()

        if matched_map:
            matched_major = matched_map[0]
            logger.info(f"Fuzzy match: '{search_major}' -> '{matched_major}'")
            mappings = major_map_crud.get_by_major_with_stats(db, matched_major, limit)
            major = matched_major
    
    # 2. Final safety: If STILL no results, return empty items with 200 OK, not error
    if not mappings:
        return RecommendationListResponse(
            items=[],
            major=search_major,
            total=0
        )
    
    # Build response
    recommendations = []
    for mapping in mappings:
        qual = mapping.qualification
        if not qual:
            continue
        
        # Get latest stats
        latest_stats = None
        if qual.stats:
            latest_stats = max(qual.stats, key=lambda s: (s.year, s.exam_round))
        
        # Calculate Dynamic Score
        # 1. Relevance (Base) - Assume mapping.score is 0-10 or 1-5. If > 5, assume 0-10.
        base_relevance = mapping.score
        if base_relevance <= 5: 
            base_relevance = base_relevance * 2 # Scale 1-5 to 2-10
            
        # 2. Demand (Candidates) - Log scale
        import math
        candidates = latest_stats.candidate_cnt if latest_stats and latest_stats.candidate_cnt else 0
        demand_score = 0
        if candidates > 0:
            # log10(100) = 2, log10(1000) = 3, log10(10000) = 4, log10(100000) = 5
            # Map 0-100k to 0-10 roughly
            demand_score = min(10, math.log10(candidates) * 2)
            
        # 3. Stability (Pass Rate)
        pass_rate = latest_stats.pass_rate if latest_stats and latest_stats.pass_rate else 0
        stability_score = (pass_rate / 100) * 10
        
        # Weighted Final Score: Relevance 60%, Demand 20%, Stability 20%
        # If no stats, rely 100% on relevance
        if latest_stats:
            final_score = (base_relevance * 0.6) + (demand_score * 0.2) + (stability_score * 0.2)
        else:
            final_score = base_relevance
            
        # Cap at 9.9 to avoid 10.0 being too common or >10
        final_score = min(9.9, final_score)
        
        recommendations.append(
            RecommendationResponse(
                qual_id=qual.qual_id,
                qual_name=qual.qual_name,
                qual_type=qual.qual_type,
                main_field=qual.main_field,
                managing_body=qual.managing_body,
                score=round(final_score, 1),
                reason=generate_recommendation_reason(mapping, latest_stats),
                latest_pass_rate=latest_stats.pass_rate if latest_stats else None
            )
        )
    
    response = RecommendationListResponse(
        items=recommendations,
        major=major,
        total=len(recommendations)
    )
    
    # Cache the response
    redis_client.set(cache_key, response.model_dump(mode="json"), get_cache_ttl())
    
    return response


@router.get(
    "/me",
    response_model=RecommendationListResponse,
    summary="Get recommendations for current user",
    description="Get certification recommendations based on the logged-in user's major."
)
async def get_my_recommendations(
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db_session),
    user_id: str = Depends(get_current_user),
    _: None = Depends(check_rate_limit)
):
    """Get recommendations based on current user's profile major."""
    # 1. Get user's major from profiles table
    row = db.execute(
        text("SELECT detail_major FROM profiles WHERE id = :id"),
        {"id": user_id}
    ).mappings().first()
    
    if not row or not row["detail_major"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="프로필에 전공 정보가 없습니다. 프로필을 먼저 설정해주세요."
        )
    
    major = row["detail_major"]
    
    # Use existing recommendation logic
    return await get_recommendations(major=major, limit=limit, db=db, _=None)


@router.get(
    "/majors",
    response_model=AvailableMajorsResponse,
    summary="Get available majors",
    description="Get list of all available majors for recommendations."
)
async def get_available_majors(
    db: Session = Depends(get_db_session),
    _: None = Depends(check_rate_limit)
):
    """Get list of available majors."""
    cache_key = "recs:majors:v5"
    
    try:
        cached = redis_client.get(cache_key)
        if cached and isinstance(cached, list):
            return {"majors": cached}
    except Exception as e:
        logger.warning(f"Cache read failed for majors list: {e}")
    
    majors = major_map_crud.get_majors_list(db)
    # Ensure it's a list before returning/caching
    if not isinstance(majors, list):
        majors = list(majors) if majors else []
        
    redis_client.set(cache_key, majors, get_cache_ttl())
    
    return {"majors": majors}


@router.get(
    "/jobs/{job_id}/certifications",
    response_model=list[JobCertificationRecommendationResponse],
    summary="Get certifications for a job",
    description="Get recommended certifications required or helpful for a specific job goal."
)
async def get_certifications_for_job(
    job_id: int,
    db: Session = Depends(get_db_session),
    _: None = Depends(check_rate_limit)
):
    """
    Get certifications for a specific job.
    SQL Design:
    SELECT 
        q.qual_name, q.main_field, j.job_name,
        j.entry_salary, j.outlook_summary
    ...
    """
    query = text("""
        SELECT 
            q.qual_id,
            q.qual_name,
            q.main_field,
            j.job_name,
            j.entry_salary,
            j.outlook_summary
        FROM qualification q
        JOIN qualification_job_map qjm ON q.qual_id = qjm.qual_id
        JOIN job j ON qjm.job_id = j.job_id
        WHERE j.job_id = :job_id
        ORDER BY q.qual_type ASC
    """)
    
    results = db.execute(query, {"job_id": job_id}).mappings().all()
    
    return [JobCertificationRecommendationResponse(**row) for row in results]


@router.get(
    "/certifications/{qual_id}/jobs",
    response_model=list[RelatedJobResponse],
    summary="Get related jobs for a certification",
    description="Get jobs that can be pursued with a specific certification."
)
async def get_jobs_for_certification(
    qual_id: int,
    db: Session = Depends(get_db_session),
    _: None = Depends(check_rate_limit)
):
    """
    Get related jobs for a certification.
    SQL Design:
    SELECT 
        j.job_name, j.reward, j.stability, j.development
    ...
    """
    query = text("""
        SELECT 
            j.job_id,
            j.job_name,
            j.reward AS salary_score,
            j.stability AS stability_score,
            j.development AS growth_score
        FROM job j
        JOIN qualification_job_map qjm ON j.job_id = qjm.job_id
        WHERE qjm.qual_id = :qual_id
        ORDER BY j.reward DESC
        LIMIT 5
    """)
    
    results = db.execute(query, {"qual_id": qual_id}).mappings().all()
    
    return [RelatedJobResponse(**row) for row in results]
