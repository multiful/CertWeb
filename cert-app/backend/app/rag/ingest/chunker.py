"""
섹션 기반 청킹: 한 자격증 내 섹션이 깨지지 않게. 표는 표 단위 유지.
현재 qualification 원문이 단일 문단이므로 RecursiveCharacterTextSplitter + section_type 태깅.
"""
from typing import List, Optional

CONTEXT_TAG_PREFIX = "[자격증명: "
CHUNK_SIZE = 1300
CHUNK_OVERLAP = 120


def section_chunk_with_metadata(
    full_content: str,
    qual_name: str,
    section_type: str = "overview",
) -> List[str]:
    """
    Recursive chunking + 각 청크 앞에 [자격증명: {name}] 태그.
    섹션 경계가 있으면 먼저 split 후 청킹할 수 있음(추후 확장).
    """
    from langchain_text_splitters import RecursiveCharacterTextSplitter

    tag = f"{CONTEXT_TAG_PREFIX}{qual_name}] "
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " "],
        length_function=len,
    )
    raw = splitter.split_text((full_content or "").strip() or "자격증")
    return [tag + c.strip() if not c.strip().startswith(CONTEXT_TAG_PREFIX) else c.strip() for c in raw]


def build_content_from_row(row: dict, related_majors: list[str] = None) -> str:
    """
    자격 한 건을 RAG 검색에 유리한 구조화된 텍스트로.
    관련 전공 정보를 포함하여 직무/전공 질의에 대한 벡터 검색 품질 개선.
    """
    qual_name = str(row.get("qual_name") or "").strip()
    qual_type = str(row.get("qual_type") or "").strip()
    main_field = str(row.get("main_field") or "").strip()
    ncs_large = str(row.get("ncs_large") or "").strip()
    managing_body = str(row.get("managing_body") or "").strip()
    grade_code = str(row.get("grade_code") or "").strip()

    parts = []
    if qual_name:
        parts.append(f"자격증명: {qual_name}")
    if qual_type:
        parts.append(f"유형: {qual_type}")
    if main_field:
        parts.append(f"분야: {main_field}")
    if ncs_large:
        parts.append(f"NCS분류: {ncs_large}")
    if managing_body:
        parts.append(f"시행기관: {managing_body}")
    if grade_code:
        parts.append(f"등급: {grade_code}")
    if related_majors:
        parts.append(f"관련전공: {', '.join(related_majors)}")

    return " | ".join(parts).replace("\n", " ").strip() or "자격증"
