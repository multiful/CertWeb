"""
청크/문서 메타데이터: cert_name, issuer, category, job_tags, difficulty, section_type, updated_year, source_url
qualification 테이블 기준으로 매핑. 부족한 필드는 기본값.
"""
from typing import Any, Optional

SECTION_TYPES = (
    "requirements",
    "subjects",
    "scoring",
    "schedule",
    "fee",
    "faq",
    "overview",
    "etc",
)


def build_chunk_metadata(
    qual_id: int,
    qual_name: str,
    qual_type: Optional[str] = None,
    main_field: Optional[str] = None,
    ncs_large: Optional[str] = None,
    managing_body: Optional[str] = None,
    grade_code: Optional[str] = None,
    section_type: str = "overview",
    chunk_index: int = 0,
    source_url: Optional[str] = None,
    updated_year: Optional[int] = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """청크 단위 메타데이터 dict. DB metadata JSONB 또는 BM25 문서에 붙일 수 있음."""
    return {
        "cert_name": qual_name or "",
        "issuer": managing_body or "",
        "category": main_field or ncs_large or "",
        "job_tags": [],  # 추후 직무태그 컬럼/소스 있으면 채움
        "difficulty": _infer_difficulty(grade_code),
        "exam_type": _infer_exam_type(qual_type),
        "requirements": [],
        "section_type": section_type if section_type in SECTION_TYPES else "etc",
        "updated_year": updated_year,
        "source_url": source_url or "",
        "qual_id": qual_id,
        "chunk_index": chunk_index,
        **{k: v for k, v in kwargs.items() if v is not None},
    }


def _infer_difficulty(grade_code: Optional[str]) -> str:
    if not grade_code:
        return "unknown"
    g = (grade_code or "").strip().upper()
    if "기사" in g or "1급" in g:
        return "high"
    if "산업기사" in g or "2급" in g:
        return "medium"
    if "기능사" in g or "3급" in g:
        return "low"
    return "unknown"


def _infer_exam_type(qual_type: Optional[str]) -> str:
    if not qual_type:
        return "unknown"
    t = (qual_type or "").strip()
    if "필기" in t and "실기" in t:
        return "both"
    if "필기" in t:
        return "written"
    if "실기" in t:
        return "practical"
    return "unknown"
