"""
DB 코퍼스 인덱싱용 canonical text/metadata 정규화 계층.

목적:
- 인덱싱 입력 문자열을 일관된 형태로 만들어 임베딩 안정성 향상
- 분야/NCS/전공 노이즈를 사전 정리해 retrieval precision 개선
"""
from __future__ import annotations

import re
import logging
import unicodedata
from typing import Any, Dict, List, Optional

from app.rag.corpus_rules import (
    DOMAIN_MISMATCH_RULES,
    MAJOR_NOISE_KEYWORDS,
    QUAL_NAMES_DOMAIN_FIX_JOOSEON,
)
from app.rag.utils.dataset_allowlist import filter_main_fields, filter_ncs_large
from app.rag.utils.domain_tokens import detect_broad_domains_in_text, get_top_domain_for_domain
from app.rag.utils.major_normalize import normalize_major

_CTRL_RE = re.compile(r"[\u0000-\u0008\u000B\u000C\u000E-\u001F\u007F]+")
_WS_RE = re.compile(r"\s+")

CANONICAL_TEXT_VERSION = "v1.0.0"
logger = logging.getLogger(__name__)


def normalize_text_for_embedding(text: Optional[str]) -> str:
    """
    임베딩 전 텍스트 정규화.
    - 유니코드 정규화(NFC)
    - 제어문자 제거
    - 다중 공백 축약
    """
    s = (text or "").strip()
    if not s:
        return ""
    s = unicodedata.normalize("NFC", s)
    s = _CTRL_RE.sub(" ", s)
    s = _WS_RE.sub(" ", s).strip()
    return s


def _apply_domain_rules(
    qual_name: str,
    main_field: str,
    ncs_large: str,
) -> tuple[str, str]:
    name = qual_name.strip()
    mf = main_field.strip()
    ncs = ncs_large.strip()

    # 조선 계열은 자동차 오분류를 조선으로 정규화
    if name in set(QUAL_NAMES_DOMAIN_FIX_JOOSEON):
        if (not mf) or ("자동차" in mf):
            mf = "조선"

    # 불일치 규칙: 자격명 키워드와 불일치한 분야/NCS는 제거
    for name_keys, wrong_keys, _reason in DOMAIN_MISMATCH_RULES:
        if not any(k in name for k in name_keys):
            continue
        if mf and any(wk in mf for wk in wrong_keys):
            mf = ""
        if ncs and any(wk in ncs for wk in wrong_keys):
            ncs = ""
    return mf, ncs


def _normalize_related_majors(qual_name: str, majors: Optional[List[str]]) -> List[str]:
    if not majors:
        return []
    normalized: List[str] = []
    for m in majors:
        nm = normalize_major(str(m or "").strip())
        if nm:
            normalized.append(nm)

    # 자격별 known noise major 키워드 제거
    for name_key, noise_terms in MAJOR_NOISE_KEYWORDS:
        if name_key in qual_name:
            normalized = [m for m in normalized if all(nt not in m for nt in noise_terms)]

    # 순서 유지 중복 제거
    seen = set()
    out: List[str] = []
    for m in normalized:
        if m in seen:
            continue
        seen.add(m)
        out.append(m)
    return out[:10]


def canonicalize_cert_row(
    row: Dict[str, Any],
    related_majors: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    qualification/certificates_vectors 원천 row를 인덱싱용 canonical dict로 변환.
    """
    try:
        qual_name = normalize_text_for_embedding(str(row.get("qual_name") or ""))
        qual_type = normalize_text_for_embedding(str(row.get("qual_type") or ""))
        main_field = normalize_text_for_embedding(str(row.get("main_field") or ""))
        ncs_large = normalize_text_for_embedding(str(row.get("ncs_large") or ""))
        managing_body = normalize_text_for_embedding(str(row.get("managing_body") or ""))
        grade_code = normalize_text_for_embedding(str(row.get("grade_code") or ""))

        main_field, ncs_large = _apply_domain_rules(qual_name, main_field, ncs_large)

        # 허용 목록 필터(비어 있으면 그대로 통과)
        main_field = (filter_main_fields([main_field]) or [""])[0] if main_field else ""
        ncs_large = (filter_ncs_large([ncs_large]) or [""])[0] if ncs_large else ""

        majors = _normalize_related_majors(qual_name, related_majors)
        domain_candidates = detect_broad_domains_in_text(
            " ".join([qual_name, main_field, ncs_large, " ".join(majors)])
        )
        domain = domain_candidates[0] if domain_candidates else ""
        top_domain = get_top_domain_for_domain(domain) if domain else None

        # DB 기존 풍부 필드 패스스루 (certificates_vectors에서 조인한 경우)
        cert_summary = normalize_text_for_embedding(str(row.get("cert_summary") or ""))
        cert_description = normalize_text_for_embedding(str(row.get("cert_description") or ""))

        return {
            "canonical_version": CANONICAL_TEXT_VERSION,
            "qual_name": qual_name,
            "qual_type": qual_type,
            "main_field": main_field,
            "ncs_large": ncs_large,
            "managing_body": managing_body,
            "grade_code": grade_code,
            "related_majors": majors,
            "domain": normalize_text_for_embedding(domain),
            "top_domain": normalize_text_for_embedding(top_domain or ""),
            "parser_route": "cert_db",
            "source": "qualification",
            "cert_summary": cert_summary,
            "cert_description": cert_description,
        }
    except Exception:
        logger.exception("canonicalize_cert_row failed: qual_id=%s", row.get("qual_id"))
        return {
            "canonical_version": CANONICAL_TEXT_VERSION,
            "qual_name": normalize_text_for_embedding(str(row.get("qual_name") or "")) or "자격증",
            "qual_type": "",
            "main_field": "",
            "ncs_large": "",
            "managing_body": "",
            "grade_code": "",
            "related_majors": [],
            "domain": "",
            "top_domain": "",
            "parser_route": "cert_db",
            "source": "qualification",
        }


def build_canonical_content(c: Dict[str, Any]) -> str:
    """
    canonical dict를 임베딩 친화 문자열로 직렬화.
    cert_summary/cert_description이 있으면 본문으로 추가해 content 길이를 권고 범위(400~600자)로 확장.
    """
    parts: List[str] = []
    if c.get("qual_name"):
        parts.append(f"자격증명: {c['qual_name']}")
    if c.get("qual_type"):
        parts.append(f"유형: {c['qual_type']}")
    if c.get("main_field"):
        parts.append(f"분야: {c['main_field']}")
    if c.get("ncs_large"):
        parts.append(f"NCS분류: {c['ncs_large']}")
    if c.get("domain"):
        parts.append(f"도메인: {c['domain']}")
    if c.get("top_domain"):
        parts.append(f"정규화도메인: {c['top_domain']}")
    if c.get("managing_body"):
        parts.append(f"시행기관: {c['managing_body']}")
    if c.get("grade_code"):
        parts.append(f"등급: {c['grade_code']}")
    majors = c.get("related_majors") or []
    if majors:
        parts.append(f"관련전공: {', '.join(majors)}")

    # DB에 이미 존재하는 풍부한 텍스트 필드 활용 (Contextual Embedding 보강)
    summary = normalize_text_for_embedding(c.get("cert_summary") or "")
    description = normalize_text_for_embedding(c.get("cert_description") or "")
    if summary:
        parts.append(f"자격증요약: {summary}")
    if description:
        parts.append(f"자격증설명: {description}")

    out = " | ".join(parts)
    return normalize_text_for_embedding(out) or "자격증"


def build_bm25_sparse_text(
    qual_id: int,
    qual_name: str,
    chunk_body: str,
    *,
    qual_type: Optional[str] = None,
    main_field: Optional[str] = None,
    ncs_large: Optional[str] = None,
    managing_body: Optional[str] = None,
    grade_code: Optional[str] = None,
    related_majors: Optional[List[str]] = None,
) -> str:
    """
    Indexing_opt.md §2·§5.3: Hybrid용 sparse(BM25) 전용 문자열(text_for_sparse).
    Dense 임베딩과 분리해 키워드·시행기관·등급·qual_id 토큰을 앞쪽에 밀도 있게 둔다.
    임베딩 API 호출 수는 늘리지 않으며, BM25 인덱스 재빌드 시 exact match 품질·역색인 비용만 증가.
    """
    head: List[str] = [f"qual_id:{qual_id}"]
    qn = (qual_name or "").strip()
    if qn:
        head.append(qn)
        head.append(qn)
    for x in (managing_body, grade_code, main_field, ncs_large, qual_type):
        xs = (x or "").strip()
        if xs:
            head.append(xs)
    if related_majors:
        for m in related_majors[:8]:
            ms = (m or "").strip()
            if ms:
                head.append(ms)
    prefix = " ".join(head)
    body = normalize_text_for_embedding(chunk_body) or ""
    if not body:
        return prefix or "자격증"
    return f"{prefix} | {body}"
