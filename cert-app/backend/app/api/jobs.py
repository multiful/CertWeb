
from typing import Optional, List
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db_session, check_rate_limit
from app.crud import job_crud
from app.schemas import JobResponse

router = APIRouter(prefix="/jobs", tags=["jobs"])

@router.get("", response_model=List[JobResponse])
async def get_jobs(
    q: Optional[str] = Query(None, description="Job name search"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db_session),
    _: None = Depends(check_rate_limit)
):
    """Search for jobs and their outlook/salary info."""
    items, _ = job_crud.get_list(db, q, page, page_size)
    return items

@router.get("/{job_id}", response_model=JobResponse)
async def get_job(
    job_id: int,
    db: Session = Depends(get_db_session),
    _: None = Depends(check_rate_limit)
):
    """Get detailed information for a specific job."""
    return job_crud.get_by_id(db, job_id)
