"""Certification API routes."""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.orm import Session
import logging

from app.api.deps import get_db_session, check_rate_limit, get_optional_user
from app.schemas import (
    QualificationListResponse,
    QualificationDetailResponse,
    QualificationListItemResponse,
    QualificationStatsListResponse,
    QualificationFilterParams,
    PassRateTrendResponse,
    TrendingQualificationListResponse,
    TrendingQualificationResponse
)
from sqlalchemy import text
from datetime import date
from app.crud import qualification_crud, stats_crud, get_qualification_aggregated_stats
from app.redis_client import redis_client
from app.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/certs", tags=["certifications"])


def get_cache_ttl(cache_type: str) -> int:
    """Get cache TTL based on type."""
    ttl_map = {
        "list": settings.CACHE_TTL_LIST,
        "detail": settings.CACHE_TTL_DETAIL,
        "stats": settings.CACHE_TTL_STATS,
    }
    return ttl_map.get(cache_type, 300)


@router.get(
    "",
    response_model=QualificationListResponse,
    summary="Get certification list",
    description="Get paginated list of certifications with search, filter, and sort options."
)
async def get_certs(
    request: Request,
    q: Optional[str] = Query(None, description="Search query for certification name"),
    main_field: Optional[str] = Query(None, description="Filter by main field"),
    ncs_large: Optional[str] = Query(None, description="Filter by NCS large category"),
    qual_type: Optional[str] = Query(None, description="Filter by qualification type"),
    managing_body: Optional[str] = Query(None, description="Filter by managing body"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    sort: str = Query("name", description="Sort by: name, pass_rate, difficulty, recent"),
    sort_desc: bool = Query(True, description="Sort direction: true for descending, false for ascending"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db_session),
    _: None = Depends(check_rate_limit)
):
    """Get certification list with filters and pagination."""
    # Build cache key
    cache_key = redis_client.make_cache_key(
        "certs:list",
        hash=redis_client.hash_query_params(
            q=q, main_field=main_field, ncs_large=ncs_large,
            qual_type=qual_type, managing_body=managing_body,
            is_active=is_active, sort=sort, sort_desc=sort_desc, page=page, page_size=page_size
        )
    )
    
    # Try cache
    cached = redis_client.get(cache_key)
    if cached:
        logger.debug("Cache hit for cert list")
        return QualificationListResponse(**cached)
    
    # Get from database
    items, total = qualification_crud.get_list(
        db,
        q=q,
        main_field=main_field,
        ncs_large=ncs_large,
        qual_type=qual_type,
        managing_body=managing_body,
        is_active=is_active,
        sort=sort,
        sort_desc=sort_desc,
        page=page,
        page_size=page_size
    )
    
    # Build response with aggregated stats
    response_items = []
    for item in items:
        stats = get_qualification_aggregated_stats(db, item.qual_id)
        response_items.append(
            QualificationListItemResponse(
                qual_id=item.qual_id,
                qual_name=item.qual_name,
                qual_type=item.qual_type,
                main_field=item.main_field,
                ncs_large=item.ncs_large,
                managing_body=item.managing_body,
                grade_code=item.grade_code,
                is_active=item.is_active,
                created_at=item.created_at,
                updated_at=item.updated_at,
                **stats
            )
        )
    
    total_pages = (total + page_size - 1) // page_size
    
    response = QualificationListResponse(
        items=response_items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )
    
    # If searching, increment trending for top results
    if q and response_items:
        # Increment trending for the top 3 results to avoid over-counting everything
        for item in response_items[:3]:
            redis_client.increment_trending("trending_certs", str(item.qual_id), amount=0.5)
            
    return response


@router.get(
    "/filter-options",
    summary="Get filter options",
    description="Get available filter values for dropdowns."
)
async def get_filter_options(
    db: Session = Depends(get_db_session),
    _: None = Depends(check_rate_limit)
):
    """Get available filter options."""
    cache_key = "certs:filter_options"
    
    cached = redis_client.get(cache_key)
    if cached:
        return cached
    
    options = qualification_crud.get_filter_options(db)
    redis_client.set(cache_key, options, get_cache_ttl("list"))
    
    return options


@router.get(
    "/{qual_id}",
    response_model=QualificationDetailResponse,
    summary="Get certification detail",
    description="Get detailed information about a specific certification."
)
async def get_cert_detail(
    qual_id: int,
    db: Session = Depends(get_db_session),
    _: None = Depends(check_rate_limit)
):
    """Get certification detail by ID."""
    cache_key = f"certs:detail:{qual_id}"
    
    # Try cache
    cached = redis_client.get(cache_key)
    if cached:
        logger.debug(f"Cache hit for cert detail: {qual_id}")
        # Increment trending traffic
        redis_client.increment_trending("trending_certs", str(qual_id), amount=1.0)
        return QualificationDetailResponse(**cached)
    
    # Get from database
    qual = qualification_crud.get_with_stats(db, qual_id)
    if not qual:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Certification with ID {qual_id} not found"
        )
    
    # Increment trending traffic for DB hit too
    redis_client.increment_trending("trending_certs", str(qual_id), amount=1.0)
    
    # Get aggregated stats
    from app.crud import get_qualification_aggregated_stats
    aggregated_stats = get_qualification_aggregated_stats(db, qual_id)
    
    response = QualificationDetailResponse(
        qual_id=qual.qual_id,
        qual_name=qual.qual_name,
        qual_type=qual.qual_type,
        main_field=qual.main_field,
        ncs_large=qual.ncs_large,
        managing_body=qual.managing_body,
        grade_code=qual.grade_code,
        is_active=qual.is_active,
        created_at=qual.created_at,
        updated_at=qual.updated_at,
        **aggregated_stats,
        stats=[
            {
                "stat_id": s.stat_id,
                "qual_id": s.qual_id,
                "year": s.year,
                "exam_round": s.exam_round,
                "candidate_cnt": s.candidate_cnt,
                "pass_cnt": s.pass_cnt,
                "pass_rate": s.pass_rate,
                "exam_structure": s.exam_structure,
                "difficulty_score": s.difficulty_score,
                "created_at": s.created_at.isoformat() if s.created_at else None,
                "updated_at": s.updated_at.isoformat() if s.updated_at else None,
            }
            for s in (qual.stats or [])
        ],
        jobs=[
            {
                "job_id": j.job_id,
                "job_name": j.job_name,
                "work_conditions": j.work_conditions,
                "outlook_summary": getattr(j, 'outlook_summary', None),
                "entry_salary": getattr(j, 'entry_salary', None),
                "similar_jobs": getattr(j, 'similar_jobs', None),
                "aptitude": getattr(j, 'aptitude', None),
                "employment_path": getattr(j, 'employment_path', None),
                "reward": getattr(j, 'reward', None),
                "stability": getattr(j, 'stability', None),
                "development": getattr(j, 'development', None),
                "condition": getattr(j, 'condition', None),
                "professionalism": getattr(j, 'professionalism', None),
                "equality": getattr(j, 'equality', None),
            }
            for j in (getattr(qual, 'jobs', []) or [])
        ]
    )
    
    # Cache the response
    redis_client.set(cache_key, response.model_dump(mode="json"), get_cache_ttl("detail"))
    
    return response


@router.get(
    "/{qual_id}/stats",
    response_model=QualificationStatsListResponse,
    summary="Get certification statistics",
    description="Get year/round statistics for a specific certification."
)
async def get_cert_stats(
    qual_id: int,
    year: Optional[int] = Query(None, description="Filter by year"),
    db: Session = Depends(get_db_session),
    _: None = Depends(check_rate_limit)
):
    """Get certification statistics."""
    cache_key = redis_client.make_cache_key(
        f"certs:stats:{qual_id}",
        year=year
    )
    
    # Try cache
    cached = redis_client.get(cache_key)
    if cached:
        logger.debug(f"Cache hit for cert stats: {qual_id}")
        return QualificationStatsListResponse(**cached)
    
    # Check if qualification exists
    qual = qualification_crud.get_by_id(db, qual_id)
    if not qual:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Certification with ID {qual_id} not found"
        )
    
    # Get stats
    stats = stats_crud.get_by_qual_id(db, qual_id, year)
    
    response = QualificationStatsListResponse(
        items=stats,
        qual_id=qual_id
    )
    
    # Cache the response
    redis_client.set(cache_key, response.model_dump(mode="json"), get_cache_ttl("stats"))
    
    return response


@router.get(
    "/{qual_id}/trends",
    response_model=list[PassRateTrendResponse],
    summary="Get pass rate trends",
    description="Get pass rate trends for the recent 3 years to analyze difficulty."
)
async def get_cert_trends(
    qual_id: int,
    db: Session = Depends(get_db_session),
    _: None = Depends(check_rate_limit)
):
    """
    Get pass rate trends for a certification (Recent 3 years).
    SQL Design:
    SELECT 
        year, exam_round, pass_rate, difficulty_score
    FROM qualification_stats
    WHERE ...
    """
    current_year = date.today().year
    start_year = current_year - 3
    
    query = text("""
        SELECT 
            year,
            exam_round,
            pass_rate,
            difficulty_score
        FROM qualification_stats
        WHERE qual_id = :qual_id
          AND year >= :start_year
        ORDER BY year DESC, exam_round DESC
    """)
    
    results = db.execute(query, {"qual_id": qual_id, "start_year": start_year}).mappings().all()
    
    if not results:
        # Fallback query with calculation if pass_rate is null but counts exist
        query_calc = text("""
            SELECT 
                year,
                exam_round,
                CASE 
                    WHEN pass_rate IS NOT NULL THEN pass_rate
                    WHEN candidate_cnt > 0 THEN (CAST(pass_cnt AS FLOAT) / candidate_cnt) * 100
                    ELSE 0
                END as pass_rate,
                difficulty_score
            FROM qualification_stats
            WHERE qual_id = :qual_id
              AND year >= :start_year
            ORDER BY year DESC, exam_round DESC
        """)
        results = db.execute(query_calc, {"qual_id": qual_id, "start_year": start_year}).mappings().all()

    return [PassRateTrendResponse(**row) for row in results]


@router.get(
    "/trending/now",
    response_model=TrendingQualificationListResponse,
    summary="Get trending certifications",
    description="Get real-time trending certifications based on user traffic (clicks/searches)."
)
async def get_trending_certs(
    limit: int = Query(10, ge=1, le=20),
    db: Session = Depends(get_db_session)
):
    """Get real-time trending certifications from Redis."""
    trending_data = redis_client.get_trending("trending_certs", limit)
    
    if not trending_data:
        # Fallback to recent popular search or defaults if Redis is empty
        return TrendingQualificationListResponse(items=[], total=0)
    
    items = []
    for qual_id_str, score in trending_data:
        qual_id = int(qual_id_str)
        qual = qualification_crud.get_by_id(db, qual_id)
        if qual:
            items.append(
                TrendingQualificationResponse(
                    qual_id=qual.qual_id,
                    qual_name=qual.qual_name,
                    qual_type=qual.qual_type,
                    main_field=qual.main_field,
                    score=score
                )
            )
            
    return TrendingQualificationListResponse(
        items=items,
        total=len(items)
    )
