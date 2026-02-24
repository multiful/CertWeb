"""User favorites API routes."""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
import logging

from app.api.deps import get_db_session, get_current_user, check_rate_limit
from app.schemas import UserFavoriteListResponse, UserFavoriteResponse
from app.crud import favorite_crud, qualification_crud
from app.redis_client import redis_client

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/me/favorites", tags=["favorites"])


def invalidate_favorites_cache(user_id: str):
    """Invalidate user's favorites cache (all versions)."""
    # Match both the old pattern and the versioned v2 pattern
    redis_client.delete_pattern(f"favorites:*{user_id}:*")


@router.get(
    "",
    response_model=UserFavoriteListResponse,
    summary="Get user favorites",
    description="Get user's favorite certifications."
)
async def get_favorites(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    db: Session = Depends(get_db_session),
    user_id: str = Depends(get_current_user),
    _: None = Depends(check_rate_limit)
):
    """Get user's favorites with optimized bulk stats."""
    cache_key = f"favorites:v5:{user_id}:{page}:{page_size}"
    
    try:
        cached = redis_client.get(cache_key)
        if cached and isinstance(cached, dict):
            return UserFavoriteListResponse(**cached)
    except Exception as e:
        logger.warning(f"Cache read failed or invalid for favorites: {e}")
    
    items, total = favorite_crud.get_by_user(db, user_id, page, page_size)
    
    # 1. Gather all qual_ids for bulk stats
    qual_ids = [fav.qual_id for fav in items if fav.qual_id]
    
    # 2. Bulk fetch aggregated stats
    from app.crud import get_qualification_aggregated_stats_bulk
    from app.schemas import QualificationListItemResponse
    
    all_stats = {}
    if qual_ids:
        try:
            all_stats = get_qualification_aggregated_stats_bulk(db, qual_ids)
        except Exception as e:
            logger.error(f"Bulk stats fetch failed: {e}")
    
    # 3. Build enriched items
    enriched_items = []
    for fav in items:
        # Prepare base favorite data
        fav_data = {
            "fav_id": fav.fav_id,
            "user_id": fav.user_id,
            "qual_id": fav.qual_id,
            "created_at": fav.created_at,
            "qualification": None
        }
        
        if fav.qualification:
            # Map stats from our bulk fetch
            stats = all_stats.get(fav.qual_id, {
                "latest_pass_rate": None,
                "avg_difficulty": None,
                "total_candidates": 0
            })
            
            try:
                # Create a reliable dict that matches QualificationListItemResponse
                q_data = {
                    "qual_id": fav.qualification.qual_id,
                    "qual_name": fav.qualification.qual_name,
                    "qual_type": fav.qualification.qual_type,
                    "main_field": fav.qualification.main_field,
                    "ncs_large": fav.qualification.ncs_large,
                    "managing_body": fav.qualification.managing_body,
                    "grade_code": fav.qualification.grade_code,
                    "is_active": fav.qualification.is_active,
                    "created_at": fav.qualification.created_at,
                    "updated_at": fav.qualification.updated_at,
                    "latest_pass_rate": stats.get("latest_pass_rate"),
                    "avg_difficulty": stats.get("avg_difficulty"),
                    "total_candidates": stats.get("total_candidates"),
                }
                fav_data["qualification"] = QualificationListItemResponse(**q_data)
            except Exception as e:
                logger.error(f"Mapping error for favorite qual_id={fav.qual_id}: {e}")
                # Fallback: create partial model from base data only to avoid 500 error
                # UserFavoriteResponse expects QualificationListItemResponse, so we must return one
                try:
                    fav_data["qualification"] = QualificationListItemResponse.from_orm(fav.qualification)
                except:
                    fav_data["qualification"] = None # Last resort

        enriched_items.append(fav_data)
    
    response = UserFavoriteListResponse(
        items=enriched_items,
        total=total
    )
    
    # Cache result defensively
    try:
        redis_client.set(cache_key, response.model_dump(mode="json"), 300)
    except Exception as e:
        logger.warning(f"Cache write failed for favorites: {e}")
    
    return response


@router.post(
    "/{qual_id}",
    response_model=UserFavoriteResponse,
    summary="Add to favorites",
    description="Add a certification to user's favorites.",
    status_code=status.HTTP_201_CREATED
)
async def add_favorite(
    qual_id: int,
    db: Session = Depends(get_db_session),
    user_id: str = Depends(get_current_user),
    _: None = Depends(check_rate_limit)
):
    """Add certification to favorites."""
    # Check if qualification exists
    qual = qualification_crud.get_by_id(db, qual_id)
    if not qual:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Certification with ID {qual_id} not found"
        )
    
    # Add to favorites
    favorite = favorite_crud.add_favorite(db, user_id, qual_id)
    
    # Invalidate cache
    invalidate_favorites_cache(user_id)
    
    return favorite


@router.delete(
    "/{qual_id}",
    summary="Remove from favorites",
    description="Remove a certification from user's favorites."
)
async def remove_favorite(
    qual_id: int,
    db: Session = Depends(get_db_session),
    user_id: str = Depends(get_current_user),
    _: None = Depends(check_rate_limit)
):
    """Remove certification from favorites."""
    success = favorite_crud.remove_favorite(db, user_id, qual_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Favorite not found"
        )
    
    # Invalidate cache
    invalidate_favorites_cache(user_id)
    
    return {"message": "Removed from favorites"}


@router.get(
    "/{qual_id}/check",
    summary="Check favorite status",
    description="Check if a certification is in user's favorites."
)
async def check_favorite(
    qual_id: int,
    db: Session = Depends(get_db_session),
    user_id: str = Depends(get_current_user),
    _: None = Depends(check_rate_limit)
):
    """Check if certification is favorited."""
    is_fav = favorite_crud.is_favorite(db, user_id, qual_id)
    
    return {
        "qual_id": qual_id,
        "is_favorite": is_fav
    }
