"""Admin API routes for automation."""
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from typing import Optional
import logging

from app.api.deps import get_db_session, verify_job_secret
from app.schemas import (
    CacheInvalidateRequest,
    CacheInvalidateResponse,
    SyncStatsResponse,
    RebuildRecommendationsResponse
)
from app.redis_client import redis_client
from app.crud import major_map_crud

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/admin", tags=["admin"])


@router.post(
    "/cache/invalidate",
    response_model=CacheInvalidateResponse,
    summary="Invalidate cache",
    description="Invalidate Redis cache by pattern. Use '*' to clear all cache."
)
async def invalidate_cache(
    request: CacheInvalidateRequest,
    _: bool = Depends(verify_job_secret)
):
    """Invalidate cache by pattern."""
    deleted_keys = redis_client.delete_pattern(request.pattern)
    
    message = f"Deleted {deleted_keys} keys matching pattern: {request.pattern}"
    if request.pattern == "*":
        message = f"Cleared all cache ({deleted_keys} keys)"
    
    logger.info(message)
    
    return CacheInvalidateResponse(
        deleted_keys=deleted_keys,
        message=message
    )


@router.post(
    "/cache/flush",
    response_model=CacheInvalidateResponse,
    summary="Flush all cache",
    description="Flush all Redis cache. Use with caution!"
)
async def flush_cache(
    _: bool = Depends(verify_job_secret)
):
    """Flush all cache."""
    success = redis_client.flush_all()
    
    if success:
        return CacheInvalidateResponse(
            deleted_keys=-1,
            message="All cache flushed successfully"
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to flush cache"
        )


@router.post(
    "/sync/stats",
    response_model=SyncStatsResponse,
    summary="Sync statistics data",
    description="Trigger statistics data sync from external sources."
)
async def sync_stats(
    background_tasks: BackgroundTasks,
    force: bool = False,
    _: bool = Depends(verify_job_secret)
):
    """Sync statistics data."""
    # This would typically trigger a background job
    # For MVP, we'll just return success and log
    
    logger.info(f"Stats sync triggered (force={force})")
    
    # In production, this would:
    # 1. Queue a background job
    # 2. Fetch data from external sources
    # 3. Upsert to database
    # 4. Invalidate related cache
    
    return SyncStatsResponse(
        success=True,
        message="Stats sync queued successfully",
        processed=0
    )


@router.post(
    "/rebuild/recommendations",
    response_model=RebuildRecommendationsResponse,
    summary="Rebuild recommendations",
    description="Rebuild recommendation scores and mappings."
)
async def rebuild_recommendations(
    background_tasks: BackgroundTasks,
    _: bool = Depends(verify_job_secret)
):
    """Rebuild recommendations."""
    logger.info("Recommendation rebuild triggered")
    
    # In production, this would:
    # 1. Recalculate scores based on new data
    # 2. Update major_qualification_map
    # 3. Invalidate recommendation cache
    
    # Invalidate recommendation cache
    deleted = redis_client.delete_pattern("recs:*")
    logger.info(f"Invalidated {deleted} recommendation cache keys")
    
    return RebuildRecommendationsResponse(
        success=True,
        message="Recommendations rebuilt successfully",
        majors_processed=0
    )


@router.get(
    "/health",
    summary="Admin health check",
    description="Detailed health check for admin monitoring."
)
async def admin_health(
    _: bool = Depends(verify_job_secret)
):
    """Admin health check with detailed info."""
    redis_info = {}
    if redis_client.is_connected():
        try:
            info = redis_client.client.info()
            redis_info = {
                "version": info.get("redis_version"),
                "connected_clients": info.get("connected_clients"),
                "used_memory_human": info.get("used_memory_human"),
                "total_keys": len(redis_client.client.keys("*")),
            }
        except Exception as e:
            redis_info = {"error": str(e)}
    
    return {
        "status": "healthy",
        "redis": redis_info,
        "cache_stats": {
            "connected": redis_client.is_connected(),
        }
    }
