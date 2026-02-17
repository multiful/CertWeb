"""Pydantic schemas for request/response validation."""
from typing import Optional, List
from pydantic import BaseModel, Field
from datetime import datetime


# ============== Base Schemas ==============

class QualificationBase(BaseModel):
    """Base qualification schema."""
    qual_name: str = Field(..., min_length=1, max_length=255)
    qual_type: Optional[str] = Field(None, max_length=100)
    main_field: Optional[str] = Field(None, max_length=100)
    ncs_large: Optional[str] = Field(None, max_length=100)
    managing_body: Optional[str] = Field(None, max_length=200)
    grade_code: Optional[str] = Field(None, max_length=50)
    is_active: bool = True


class QualificationStatsBase(BaseModel):
    """Base qualification stats schema."""
    year: int = Field(..., ge=1900, le=2100)
    exam_round: int = Field(..., ge=1)
    candidate_cnt: Optional[int] = Field(None, ge=0)
    pass_cnt: Optional[int] = Field(None, ge=0)
    pass_rate: Optional[float] = Field(None, ge=0, le=100)
    exam_structure: Optional[str] = None
    difficulty_score: Optional[float] = Field(None, ge=0, le=10)


class MajorQualificationMapBase(BaseModel):
    """Base major-qualification mapping schema."""
    major: str = Field(..., min_length=1, max_length=100)
    score: float = Field(default=1.0, ge=0, le=10)
    weight: Optional[float] = Field(None, ge=0, le=10)
    reason: Optional[str] = Field(None, max_length=500)


# ============== Response Schemas ==============

class QualificationStatsResponse(QualificationStatsBase):
    """Qualification stats response schema."""
    stat_id: Optional[int] = None
    qual_id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class QualificationResponse(QualificationBase):
    """Qualification response schema."""
    qual_id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class JobResponse(BaseModel):
    """Job information response schema."""
    job_id: int
    job_name: str
    work_conditions: Optional[str] = None
    
    # New fields
    outlook_summary: Optional[str] = None
    entry_salary: Optional[str] = None
    
    # Radar chart points
    reward: Optional[float] = None
    stability: Optional[float] = None
    development: Optional[float] = None
    condition: Optional[float] = None
    professionalism: Optional[float] = None
    equality: Optional[float] = None
    
    # Text-heavy detail fields
    similar_jobs: Optional[str] = None
    aptitude: Optional[str] = None
    employment_path: Optional[str] = None
    
    # Related certifications
    qualifications: List[QualificationResponse] = []
    
    class Config:
        from_attributes = True


class QualificationDetailResponse(QualificationResponse):
    """Qualification detail response with stats and related jobs."""
    stats: List[QualificationStatsResponse] = []
    jobs: List[JobResponse] = []
    latest_pass_rate: Optional[float] = None
    avg_difficulty: Optional[float] = None
    total_candidates: Optional[int] = None


class QualificationListItemResponse(QualificationResponse):
    """Qualification list item with aggregated stats."""
    latest_pass_rate: Optional[float] = None
    avg_difficulty: Optional[float] = None
    total_candidates: Optional[int] = None


class RecommendationResponse(BaseModel):
    """Recommendation response schema."""
    qual_id: int
    qual_name: str
    qual_type: Optional[str] = None
    main_field: Optional[str] = None
    managing_body: Optional[str] = None
    score: float
    reason: Optional[str] = None
    latest_pass_rate: Optional[float] = None


class JobCertificationRecommendationResponse(BaseModel):
    """Schema for certification recommendations for a specific job."""
    qual_id: int
    qual_name: str
    main_field: Optional[str] = None
    job_name: str
    entry_salary: Optional[str] = None
    outlook_summary: Optional[str] = None


class RelatedJobResponse(BaseModel):
    """Schema for related jobs for a specific certification."""
    job_id: int
    job_name: str
    salary_score: Optional[float] = None
    stability_score: Optional[float] = None
    growth_score: Optional[float] = None


class MajorQualificationMapResponse(MajorQualificationMapBase):
    """Major-qualification mapping response schema."""
    map_id: int
    qual_id: int
    qualification: Optional[QualificationResponse] = None
    
    class Config:
        from_attributes = True


class UserFavoriteResponse(BaseModel):
    """User favorite response schema."""
    fav_id: int
    user_id: str
    qual_id: int
    created_at: datetime
    qualification: Optional[QualificationResponse] = None
    
    class Config:
        from_attributes = True


class MajorResponse(BaseModel):
    """Major/Department response schema."""
    major_id: int
    major_name: str
    major_category: Optional[str] = None
    
    class Config:
        from_attributes = True


class PassRateTrendResponse(BaseModel):
    """Schema for certification pass rate trends."""
    year: int
    exam_round: int
    pass_rate: Optional[float] = None
    difficulty_score: Optional[float] = None


# ============== List Response Schemas ==============

class PaginatedResponse(BaseModel):
    """Base paginated response."""
    total: int
    page: int
    page_size: int
    total_pages: int


class QualificationListResponse(PaginatedResponse):
    """Qualification list response."""
    items: List[QualificationListItemResponse]


class QualificationStatsListResponse(BaseModel):
    """Qualification stats list response."""
    items: List[QualificationStatsResponse]
    qual_id: int


class RecommendationListResponse(BaseModel):
    """Recommendation list response."""
    items: List[RecommendationResponse]
    major: str
    total: int


class UserFavoriteListResponse(BaseModel):
    """User favorite list response."""
    items: List[UserFavoriteResponse]
    total: int


class MajorListResponse(PaginatedResponse):
    """Major list response."""
    items: List[MajorResponse]


# ============== Request Schemas ==============

class QualificationCreate(QualificationBase):
    """Create qualification request."""
    pass


class QualificationUpdate(BaseModel):
    """Update qualification request."""
    qual_name: Optional[str] = Field(None, min_length=1, max_length=255)
    qual_type: Optional[str] = Field(None, max_length=100)
    main_field: Optional[str] = Field(None, max_length=100)
    ncs_large: Optional[str] = Field(None, max_length=100)
    managing_body: Optional[str] = Field(None, max_length=200)
    grade_code: Optional[str] = Field(None, max_length=50)
    is_active: Optional[bool] = None


class QualificationStatsCreate(QualificationStatsBase):
    """Create qualification stats request."""
    qual_id: int


class QualificationStatsUpdate(BaseModel):
    """Update qualification stats request."""
    year: Optional[int] = Field(None, ge=1900, le=2100)
    exam_round: Optional[int] = Field(None, ge=1)
    candidate_cnt: Optional[int] = Field(None, ge=0)
    pass_cnt: Optional[int] = Field(None, ge=0)
    pass_rate: Optional[float] = Field(None, ge=0, le=100)
    exam_structure: Optional[str] = None
    difficulty_score: Optional[float] = Field(None, ge=0, le=10)


class MajorQualificationMapCreate(MajorQualificationMapBase):
    """Create major-qualification mapping request."""
    qual_id: int


# ============== Query Parameter Schemas ==============

class QualificationFilterParams(BaseModel):
    """Qualification filter query parameters."""
    q: Optional[str] = None
    main_field: Optional[str] = None
    ncs_large: Optional[str] = None
    qual_type: Optional[str] = None
    managing_body: Optional[str] = None
    is_active: Optional[bool] = None
    sort: str = "name"  # name, pass_rate, difficulty, recent
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class RecommendationQueryParams(BaseModel):
    """Recommendation query parameters."""
    major: str = Field(..., min_length=1)
    limit: int = Field(default=10, ge=1, le=50)


# ============== Health Check Schema ==============

class HealthCheckResponse(BaseModel):
    """Health check response."""
    status: str
    database: str
    redis: str
    version: str = "1.0.0"


# ============== Admin Schemas ==============

class CacheInvalidateRequest(BaseModel):
    """Cache invalidation request."""
    pattern: str = "*"


class CacheInvalidateResponse(BaseModel):
    """Cache invalidation response."""
    deleted_keys: int
    message: str


class SyncStatsResponse(BaseModel):
    """Sync stats response."""
    success: bool
    message: str
    processed: int = 0


class RebuildRecommendationsResponse(BaseModel):
    """Rebuild recommendations response."""
    success: bool
    message: str
    majors_processed: int = 0
