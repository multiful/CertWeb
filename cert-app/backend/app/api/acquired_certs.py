"""User acquired certifications API. Profile(user)별 취득 자격증 목록·추가·삭제·요약."""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
import logging

from app.api.deps import get_db_session, get_current_user, check_rate_limit
from app.schemas import UserAcquiredCertListResponse, UserAcquiredCertResponse, QualificationListItemResponse
from app.crud import acquired_cert_crud, qualification_crud
from app.crud import get_qualification_aggregated_stats_bulk
from app.utils.xp import (
    calculate_cert_xp,
    get_level_from_xp,
    get_tier_from_level,
    get_xp_for_next_level,
    get_xp_for_current_level,
    TIER_INFO,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/me/acquired-certs", tags=["acquired-certs"])


def _enrich_item(acq, all_stats: dict) -> UserAcquiredCertResponse:
    """Build UserAcquiredCertResponse with qualification, stats, and xp."""
    qual = getattr(acq, "qualification", None)
    if not qual:
        return UserAcquiredCertResponse(
            acq_id=acq.acq_id,
            user_id=acq.user_id,
            qual_id=acq.qual_id,
            acquired_at=acq.acquired_at,
            created_at=acq.created_at,
            xp=calculate_cert_xp(None),
            qualification=None,
        )
    stats = all_stats.get(acq.qual_id, {}) if acq.qual_id else {}
    avg_diff = stats.get("avg_difficulty")
    xp = calculate_cert_xp(avg_diff)
    q_data = {
        "qual_id": qual.qual_id,
        "qual_name": qual.qual_name,
        "qual_type": qual.qual_type,
        "main_field": qual.main_field,
        "ncs_large": qual.ncs_large,
        "managing_body": qual.managing_body,
        "grade_code": qual.grade_code,
        "is_active": qual.is_active,
        "created_at": qual.created_at,
        "updated_at": qual.updated_at,
        "latest_pass_rate": stats.get("latest_pass_rate"),
        "avg_difficulty": avg_diff,
        "total_candidates": stats.get("total_candidates"),
    }
    return UserAcquiredCertResponse(
        acq_id=acq.acq_id,
        user_id=acq.user_id,
        qual_id=acq.qual_id,
        acquired_at=acq.acquired_at,
        created_at=acq.created_at,
        xp=xp,
        qualification=QualificationListItemResponse(**q_data),
    )


@router.get(
    "",
    response_model=UserAcquiredCertListResponse,
    summary="Get acquired certs",
    description="Get current user's acquired certifications with XP.",
)
async def get_acquired_certs(
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=200),
    db: Session = Depends(get_db_session),
    user_id: str = Depends(get_current_user),
    _: None = Depends(check_rate_limit),
):
    """List user's acquired certs with qualification info and xp."""
    items, total = acquired_cert_crud.get_by_user(db, user_id, page, page_size)
    qual_ids = [a.qual_id for a in items if a.qual_id]
    all_stats = {}
    if qual_ids:
        try:
            all_stats = get_qualification_aggregated_stats_bulk(db, qual_ids)
        except Exception as e:
            logger.warning("Bulk stats for acquired certs: %s", e)
    list_items = [_enrich_item(a, all_stats) for a in items]
    return UserAcquiredCertListResponse(items=list_items, total=total)


@router.get(
    "/count",
    summary="Count acquired certs",
)
async def get_acquired_certs_count(
    db: Session = Depends(get_db_session),
    user_id: str = Depends(get_current_user),
    _: None = Depends(check_rate_limit),
):
    """Return count only (lightweight, for card display)."""
    count = acquired_cert_crud.count_by_user(db, user_id)
    return {"count": count}


@router.get(
    "/summary",
    summary="XP summary with level and tier",
    description="Returns total_xp, level, tier and progress for the current user.",
)
async def get_acquired_certs_summary(
    db: Session = Depends(get_db_session),
    user_id: str = Depends(get_current_user),
    _: None = Depends(check_rate_limit),
):
    """Compute total XP, level, and tier from all acquired certs."""
    items, _ = acquired_cert_crud.get_by_user(db, user_id, page=1, page_size=500)
    qual_ids = [a.qual_id for a in items if a.qual_id]
    all_stats: dict = {}
    if qual_ids:
        try:
            all_stats = get_qualification_aggregated_stats_bulk(db, qual_ids)
        except Exception as e:
            logger.warning("Bulk stats for summary: %s", e)

    total_xp = 0.0
    for a in items:
        stats = all_stats.get(a.qual_id, {}) if a.qual_id else {}
        avg_diff = stats.get("avg_difficulty")
        total_xp += calculate_cert_xp(avg_diff)

    level = get_level_from_xp(total_xp)
    tier = get_tier_from_level(level)
    tier_meta = TIER_INFO.get(tier, {})
    return {
        "total_xp": round(total_xp, 2),
        "level": level,
        "tier": tier,
        "tier_color": tier_meta.get("color", "#fff"),
        "current_level_xp": get_xp_for_current_level(level),
        "next_level_xp": get_xp_for_next_level(level),
        "cert_count": len(items),
    }


@router.post(
    "/{qual_id}",
    response_model=UserAcquiredCertResponse,
    summary="Add acquired cert",
    status_code=status.HTTP_201_CREATED,
)
async def add_acquired_cert(
    qual_id: int,
    db: Session = Depends(get_db_session),
    user_id: str = Depends(get_current_user),
    _: None = Depends(check_rate_limit),
):
    """Add certification to acquired list. 이미 있으면 200으로 기존 항목 반환."""
    qual = qualification_crud.get_by_id(db, qual_id)
    if not qual:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Certification not found")
    acq = acquired_cert_crud.add(db, user_id, qual_id)
    all_stats: dict = {}
    try:
        all_stats = get_qualification_aggregated_stats_bulk(db, [qual_id])
    except Exception:
        pass
    return _enrich_item(acq, all_stats)


@router.delete(
    "/{qual_id}",
    summary="Remove acquired cert",
)
async def remove_acquired_cert(
    qual_id: int,
    db: Session = Depends(get_db_session),
    user_id: str = Depends(get_current_user),
    _: None = Depends(check_rate_limit),
):
    """Remove from acquired list."""
    ok = acquired_cert_crud.remove(db, user_id, qual_id)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Acquired cert not found")
    return {"message": "Removed"}
