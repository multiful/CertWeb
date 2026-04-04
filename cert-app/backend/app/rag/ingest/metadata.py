"""
청크/문서 메타데이터: cert_name, issuer, category, job_tags, difficulty, section_type, updated_year, source_url
qualification 테이블 기준으로 매핑. 부족한 필드는 기본값.

Indexing_opt.md 4.6: 필수(doc_id, chunk_type, access_scope 등) + 권장(section_path, parent_id, indexed_at) 반영.
DB 코퍼스는 PDF 페이지가 없으면 page_no는 null, parent_id는 chunk_index>0일 때 부모 청크 참조.
"""
from datetime import datetime, timezone
import logging
import os
from typing import Any, Optional
from app.rag.ingest.canonical_text import CANONICAL_TEXT_VERSION

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
logger = logging.getLogger(__name__)

_emb_model_cache: Optional[str] = None


def _embedding_model_label() -> str:
    """Indexing_opt §5: 재색인·drift 비교용 임베딩 모델 라벨."""
    global _emb_model_cache
    if _emb_model_cache is not None:
        return _emb_model_cache
    try:
        from app.config import get_settings

        _emb_model_cache = (get_settings().OPENAI_EMBEDDING_MODEL or "text-embedding-3-small").strip()
    except Exception:
        _emb_model_cache = (os.environ.get("OPENAI_EMBEDDING_MODEL") or "text-embedding-3-small").strip()
    return _emb_model_cache


def _default_parent_id(qual_id: int, chunk_index: int) -> Optional[str]:
    """부모 청크 참조: chunk_index==0 이면 루트(부모 없음), 그 외에는 문서의 첫 청크를 부모로."""
    if chunk_index == 0:
        return None
    return f"{qual_id}:chunk_0"


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
    written_cnt: Optional[int] = None,
    practical_cnt: Optional[int] = None,
    page_no: Optional[int] = None,
    parent_id: Optional[str] = None,
    access_scope: str = "public",
    indexed_at: Optional[str] = None,
    chunk_hash: Optional[str] = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """청크 단위 메타데이터 dict. DB metadata JSONB 또는 BM25 문서에 붙일 수 있음."""
    try:
        ts = indexed_at or datetime.now(timezone.utc).isoformat()
        pid = parent_id if parent_id is not None else _default_parent_id(qual_id, chunk_index)
        return {
            "canonical_version": CANONICAL_TEXT_VERSION,
            "parser_route": "cert_db",
            "source": "qualification",
            # Indexing_opt.md 4.6 필수 필드
            "doc_id": str(qual_id),                                      # 문서 단위 식별 및 삭제 동기화
            "chunk_type": "text",                                         # text/table/code 구분 (DB 코퍼스는 항상 text)
            "access_scope": access_scope,                                 # 단일 테넌트 서비스: public
            "section_path": _build_section_path(main_field, ncs_large),  # 계층 컨텍스트 (권장)
            "page_no": page_no,                                           # PDF 출처 시 페이지 (DB만 쓰면 null)
            "parent_id": pid,                                             # 권장: 부모 청크 id
            "indexed_at": ts,                                             # 권장: 색인 시각 (TTL/신선도)
            "created_at": ts,                                             # 4.6 권장: 메타 TTL·감사(동일 시각으로 기록)
            "emb_model_version": _embedding_model_label(),              # §5 Dense baseline / drift 추적
            "sparse_text_version": "v1",                                  # BM25 전용 문자열 포맷 버전
            # 기존 필드
            "cert_name": qual_name or "",
            "issuer": managing_body or "",
            "category": main_field or ncs_large or "",
            "job_tags": [],
            "difficulty": _infer_difficulty(grade_code),
            "exam_type": _infer_exam_type(qual_type, written_cnt, practical_cnt),
            "requirements": [],
            "section_type": section_type if section_type in SECTION_TYPES else "etc",
            "updated_year": updated_year,
            "source_url": source_url or "",
            "qual_id": qual_id,
            "chunk_index": chunk_index,
            **({"chunk_hash": chunk_hash} if chunk_hash else {}),
            **{k: v for k, v in kwargs.items() if v is not None},
        }
    except Exception:
        logger.exception("build_chunk_metadata failed: qual_id=%s chunk_index=%s", qual_id, chunk_index)
        return {
            "canonical_version": CANONICAL_TEXT_VERSION,
            "parser_route": "cert_db",
            "source": "qualification",
            "doc_id": str(qual_id),
            "chunk_type": "text",
            "access_scope": "public",
            "section_path": "",
            "page_no": None,
            "parent_id": None,
            "indexed_at": datetime.now(timezone.utc).isoformat(),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "emb_model_version": _embedding_model_label(),
            "sparse_text_version": "v1",
            "cert_name": str(qual_name or ""),
            "issuer": "",
            "category": "",
            "job_tags": [],
            "difficulty": "unknown",
            "exam_type": "unknown",
            "requirements": [],
            "section_type": "etc",
            "updated_year": None,
            "source_url": "",
            "qual_id": qual_id,
            "chunk_index": chunk_index,
        }


def _build_section_path(main_field: Optional[str], ncs_large: Optional[str]) -> str:
    """
    분야/NCS 계층으로 section_path 생성.
    ex) "기계 > 기계설계"
    """
    parts = [p.strip() for p in [main_field, ncs_large] if p and p.strip()]
    return " > ".join(parts) if parts else ""


def _infer_difficulty(grade_code: Optional[str]) -> str:
    if not grade_code:
        return "unknown"
    g = (grade_code or "").strip().upper()
    if "기술사" in g:
        return "expert"
    if "기사" in g or "1급" in g:
        return "high"
    if "산업기사" in g or "2급" in g:
        return "medium"
    if "기능사" in g or "3급" in g:
        return "low"
    return "unknown"


def _infer_exam_type(
    qual_type: Optional[str],
    written_cnt: Optional[int] = None,
    practical_cnt: Optional[int] = None,
) -> str:
    """
    written_cnt/practical_cnt(qualification 테이블 실측값)를 우선 사용.
    없으면 qual_type 문자열로 fallback.
    """
    has_written = (written_cnt or 0) > 0
    has_practical = (practical_cnt or 0) > 0
    if has_written or has_practical:
        if has_written and has_practical:
            return "both"
        if has_written:
            return "written"
        return "practical"
    # fallback: qual_type 문자열 파싱
    t = (qual_type or "").strip()
    if not t:
        return "unknown"
    if "필기" in t and "실기" in t:
        return "both"
    if "필기" in t:
        return "written"
    if "실기" in t:
        return "practical"
    return "unknown"
