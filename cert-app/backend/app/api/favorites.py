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
    """Invalidate user's favorites cache."""
    redis_client.delete_pattern(f"favorites:{user_id}:*")


@router.get(
    "",
    response_model=UserFavoriteListResponse,
    summary="Get user favorites",
    description="Get user's favorite certifications."
)
async def get_favorites(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=1000),
    db: Session = Depends(get_db_session),
    user_id: str = Depends(get_current_user),
    _: None = Depends(check_rate_limit)
):
    """Get user's favorites."""
    cache_key = f"favorites:{user_id}:{page}:{page_size}"
    
    cached = redis_client.get(cache_key)
    if cached:
        return UserFavoriteListResponse(**cached)
    
    items, total = favorite_crud.get_by_user(db, user_id, page, page_size)
    
    response = UserFavoriteListResponse(
        items=items,
        total=total
    )
    
    redis_client.set(cache_key, response.model_dump(mode="json"), 300)
    
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
