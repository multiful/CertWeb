"""
섹션 기반 청킹: 한 자격증 내 섹션이 깨지지 않게. 표는 표 단위 유지.
현재 qualification 원문이 단일 문단이므로 RecursiveCharacterTextSplitter + section_type 태깅.
"""
import os
import logging
from typing import Dict, List, Optional, Tuple

from app.rag.ingest.canonical_text import (
    CANONICAL_TEXT_VERSION,
    build_canonical_content,
    canonicalize_cert_row,
)

CONTEXT_TAG_PREFIX = "[자격증명: "
# Indexing_opt §4.3: 규정·매뉴얼형 권장 400~600 토큰·오버랩 10~15% (한국어는 문자 기준 대략 2~3배 휴리스틱)
CHUNK_SIZE = 1300
CHUNK_OVERLAP = 120

# balanced 기준 + 실험군 프로파일 (chars, overlap, min_tail_merge)
CHUNK_PROFILES: Dict[str, Tuple[int, int, int]] = {
    "baseline": (1300, 120, 180),
    "exp_small": (900, 90, 140),
    "exp_medium": (1100, 120, 160),
    "exp_large": (1400, 160, 220),
}
logger = logging.getLogger(__name__)


def _resolve_chunk_profile(profile: Optional[str]) -> Tuple[int, int, int]:
    p = (profile or os.environ.get("RAG_CHUNK_PROFILE") or "baseline").strip()
    resolved = CHUNK_PROFILES.get(p, CHUNK_PROFILES["baseline"])
    if p not in CHUNK_PROFILES:
        logger.warning("unknown chunk profile '%s', fallback to baseline", p)
    return resolved


def _merge_short_tail(chunks: List[str], min_tail_chars: int) -> List[str]:
    """
    마지막 꼬리 청크가 지나치게 짧으면 이전 청크와 병합해 문맥 단절 완화.
    """
    if len(chunks) < 2:
        return chunks
    last = chunks[-1].strip()
    if len(last) >= min_tail_chars:
        return chunks
    merged = chunks[:-2] + [f"{chunks[-2].rstrip()} {last}".strip()]
    return merged


def section_chunk_with_metadata(
    full_content: str,
    qual_name: str,
    section_type: str = "overview",
    profile: Optional[str] = None,
) -> List[str]:
    """
    Recursive chunking + 각 청크 앞에 [자격증명: {name}] 태그.
    섹션 경계가 있으면 먼저 split 후 청킹할 수 있음(추후 확장).
    """
    try:
        from langchain_text_splitters import RecursiveCharacterTextSplitter

        tag = f"{CONTEXT_TAG_PREFIX}{qual_name}] "
        chunk_size, chunk_overlap, min_tail_chars = _resolve_chunk_profile(profile)
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", ". ", " "],
            length_function=len,
        )
        raw = splitter.split_text((full_content or "").strip() or "자격증")
        raw = [c.strip() for c in raw if c and c.strip()]
        raw = _merge_short_tail(raw, min_tail_chars=min_tail_chars)
        chunks = [tag + c if not c.startswith(CONTEXT_TAG_PREFIX) else c for c in raw]
        logger.debug(
            "chunked content: qual_name=%s section=%s profile=%s chunks=%s",
            qual_name,
            section_type,
            profile or os.environ.get("RAG_CHUNK_PROFILE") or "baseline",
            len(chunks),
        )
        return chunks
    except Exception:
        logger.exception("chunking failed: qual_name=%s section=%s", qual_name, section_type)
        safe = (full_content or "").strip() or "자격증"
        return [f"{CONTEXT_TAG_PREFIX}{qual_name}] {safe}"]


def build_content_from_row(row: dict, related_majors: list[str] = None) -> str:
    """
    자격 한 건을 RAG 검색에 유리한 구조화된 텍스트로.
    관련 전공 정보를 포함하여 직무/전공 질의에 대한 벡터 검색 품질 개선.
    """
    try:
        canonical = canonicalize_cert_row(row=row, related_majors=related_majors or [])
        return build_canonical_content(canonical)
    except Exception:
        logger.exception("build_content_from_row failed: qual_id=%s", row.get("qual_id"))
        return str(row.get("qual_name") or "자격증").strip() or "자격증"


def build_canonical_metadata_from_row(row: dict, related_majors: list[str] = None) -> dict:
    """
    인덱싱 시 메타데이터 기본값으로 사용할 canonical 파생값.
    """
    try:
        canonical = canonicalize_cert_row(row=row, related_majors=related_majors or [])
        return {
            "canonical_version": CANONICAL_TEXT_VERSION,
            "parser_route": canonical.get("parser_route", "cert_db"),
            "source": canonical.get("source", "qualification"),
            "domain": canonical.get("domain", ""),
            "top_domain": canonical.get("top_domain", ""),
            "related_majors": canonical.get("related_majors", []),
        }
    except Exception:
        logger.exception("build_canonical_metadata_from_row failed: qual_id=%s", row.get("qual_id"))
        return {
            "canonical_version": CANONICAL_TEXT_VERSION,
            "parser_route": "cert_db",
            "source": "qualification",
            "domain": "",
            "top_domain": "",
            "related_majors": [],
        }
