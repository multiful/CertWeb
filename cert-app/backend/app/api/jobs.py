
from typing import Optional, List
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db_session, check_rate_limit
from app.crud import job_crud
from app.schemas import JobResponse

router = APIRouter(prefix="/jobs", tags=["jobs"])

from app.redis_client import redis_client

@router.get("", response_model=List[JobResponse])
async def get_jobs(
    q: Optional[str] = Query(None, description="Job name search"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db_session),
    _: None = Depends(check_rate_limit)
):
    """Search for jobs and their outlook/salary info."""
    cache_key = f"jobs:list:v2:{q}:{page}:{page_size}"
    
    try:
        cached = redis_client.get(cache_key)
        if cached:
            if isinstance(cached, str):
                import orjson
                cached = orjson.loads(cached)
            
            if isinstance(cached, list):
                return cached
    except Exception:
        pass

    items, _ = job_crud.get_list(db, q, page, page_size)
    
    # Store directly as lists of dicts
    result = [JobResponse.model_validate(item).model_dump() for item in items]
    redis_client.set(cache_key, result, 3600)  # cache for 1 hour
    
    return result

@router.get("/{job_id}", response_model=JobResponse)
async def get_job(
    job_id: int,
    db: Session = Depends(get_db_session),
    _: None = Depends(check_rate_limit)
):
    """Get detailed information for a specific job."""
    cache_key = f"jobs:detail:v2:{job_id}"
    
    try:
        cached = redis_client.get(cache_key)
        if cached:
            if isinstance(cached, str):
                import orjson
                cached = orjson.loads(cached)
            
            if isinstance(cached, dict):
                return cached
    except Exception:
        pass

    job = job_crud.get_by_id(db, job_id)
    if not job:
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found"
        )
        
    result = JobResponse.model_validate(job).model_dump()
    redis_client.set(cache_key, result, 3600)
    
    return result
