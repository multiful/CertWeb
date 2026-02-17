
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db_session, check_rate_limit
from app.crud import major_crud
from app.schemas import MajorResponse, MajorListResponse

router = APIRouter(prefix="/majors", tags=["majors"])


@router.get(
    "",
    response_model=MajorListResponse,
    summary="List majors",
    description="Get a paginated list of majors. Supports search by major name."
)
async def get_majors(
    q: Optional[str] = Query(None, description="Search query for major name"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db_session),
    _: None = Depends(check_rate_limit)
):
    """
    Get paginated list of majors.
    """
    items, total = major_crud.get_list(db, q, page, page_size)
    
    total_pages = (total + page_size - 1) // page_size
    
    return MajorListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )
