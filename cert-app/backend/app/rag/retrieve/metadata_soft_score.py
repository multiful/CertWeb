"""
Metadata 기반 soft scoring: 직무/전공/추천대상 일치 시 가산, 분야 이탈 시 감점.
쿼리 도메인(IT·디지털 집중 vs 그 외) ↔ 자격 메타 불일치 시 감점(선택, RAG_METADATA_DOMAIN_MISMATCH_ENABLE).
전공 비교 시 쿼리/자격증 모두 major_category로 정규화해 매칭률을 높임.
"""
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session
from sqlalchemy import text

from app.rag.utils.major_normalize import normalize_major


# 기본 가중치 (config로 오버라이드)
DEFAULT_JOB_BONUS = 0.15
DEFAULT_MAJOR_BONUS = 0.10
DEFAULT_TARGET_BONUS = 0.10
DEFAULT_FIELD_PENALTY = -0.20
DEFAULT_DOMAIN_MISMATCH_PENALTY = -0.35
DEFAULT_DOMAIN_BONUS = 0.15
DEFAULT_DOMAIN_KEYWORD_BONUS = 0.08


def _normalize_tokens(s: str) -> set:
    """공백/쉼표 분리, 소문자 없음(한글)."""
    if not s or not isinstance(s, str):
        return set()
    return set(t.strip() for t in s.replace(",", " ").split() if t.strip())


def _tokens_from_maybe_list(v: Any) -> set:
    """문자열/리스트 입력을 토큰 set으로 정규화."""
    if v is None:
        return set()
    if isinstance(v, list):
        return _normalize_tokens(" ".join(str(x) for x in v if str(x).strip()))
    return _normalize_tokens(str(v))


def _normalize_major_token_set(s: str) -> set:
    """
    쿼리 전공 문자열을 토큰 단위로 major_category 정규화.
    예) "컴퓨터공학과 소프트웨어학과" -> {"컴퓨터공학과", "응용소프트웨어공학과", ...}
    """
    out = set()
    for tok in _normalize_tokens(s):
        n = normalize_major(tok)
        if n:
            out.add(n)
    return out


def _overlap_ratio(a: set, b: set) -> float:
    if not b:
        return 0.0
    return len(a & b) / len(b) if b else 0.0


def compute_metadata_soft_score(
    query_slots: Dict[str, Any],
    qual_metadata: Dict[str, Any],
    config: Dict[str, Any] | None = None,
    query_is_it: Optional[bool] = None,
) -> float:
    """
    query_slots: rewrite에서 추출한 전공, 희망직무, 목적 등.
    qual_metadata: qualification + related_majors 등 (main_field, ncs_large, related_majors, is_it).
    config: RAG_METADATA_SOFT_* 가중치. domain_mismatch_penalty 있으면 도메인 불일치 시 적용.
    query_is_it: 쿼리가 IT 도메인인지. None이면 도메인 불일치 미적용.
    """
    cfg = config or {}
    job_bonus = float(cfg.get("job_bonus", DEFAULT_JOB_BONUS))
    major_bonus = float(cfg.get("major_bonus", DEFAULT_MAJOR_BONUS))
    target_bonus = float(cfg.get("target_bonus", DEFAULT_TARGET_BONUS))
    field_penalty = float(cfg.get("field_penalty", DEFAULT_FIELD_PENALTY))
    domain_mismatch_penalty = float(cfg.get("domain_mismatch_penalty", 0.0))
    domain_bonus = float(cfg.get("domain_bonus", DEFAULT_DOMAIN_BONUS))
    domain_keyword_bonus = float(cfg.get("domain_keyword_bonus", DEFAULT_DOMAIN_KEYWORD_BONUS))
    main_field_in_job_match = bool(cfg.get("main_field_in_job_match", True))

    score = 0.0
    q_job = _normalize_tokens(str(query_slots.get("희망직무") or query_slots.get("관심분야") or ""))
    q_major = _normalize_major_token_set(str(query_slots.get("전공") or ""))
    q_interest = _normalize_tokens(str(query_slots.get("관심분야") or ""))
    q_domains = _normalize_tokens(str(query_slots.get("도메인") or ""))
    q_top_domain = _normalize_tokens(str(query_slots.get("정규화도메인") or ""))
    q_domain_keywords = _normalize_tokens(str(query_slots.get("도메인_키워드") or ""))
    q_main_field = _normalize_tokens(str(query_slots.get("분야") or ""))
    q_ncs = _normalize_tokens(str(query_slots.get("NCS대분류") or ""))

    qual_main_fields = _tokens_from_maybe_list(qual_metadata.get("main_fields"))
    qual_ncs_list = _tokens_from_maybe_list(qual_metadata.get("ncs_large_list"))
    mf_tokens = (
        _normalize_tokens(str(qual_metadata.get("main_field") or ""))
        if main_field_in_job_match
        else set()
    )
    qual_job = (
        mf_tokens
        | _normalize_tokens(str(qual_metadata.get("ncs_large") or ""))
        | qual_main_fields
        | qual_ncs_list
    )
    qual_majors = qual_metadata.get("related_majors") or []
    if isinstance(qual_majors, list):
        qual_major_set = set()
        for m in qual_majors:
            n = normalize_major(str(m).strip())
            if n:
                qual_major_set.add(n)
    else:
        qual_major_set = {normalize_major(str(qual_majors).strip())} if str(qual_majors).strip() else set()

    if q_job and qual_job and _overlap_ratio(q_job, qual_job) > 0:
        score += job_bonus
    if q_major and qual_major_set and _overlap_ratio(q_major, qual_major_set) > 0:
        score += major_bonus
    if q_interest and qual_job and _overlap_ratio(q_interest, qual_job) > 0:
        score += target_bonus * 0.5
    if q_job and qual_job and len(qual_job) > 0 and _overlap_ratio(q_job, qual_job) == 0 and len(q_job) >= 2:
        score += field_penalty * 0.5

    # 넓은 도메인(IT/금융/의료/관광 등) 일치 시 가산
    qual_domains = _normalize_tokens(
        " ".join(
            (qual_metadata.get("domains") or [])
            + [str(qual_metadata.get("cert_domain") or ""), str(qual_metadata.get("cert_top_domain") or "")]
        )
    )
    qual_domain_keywords = _normalize_tokens(str(qual_metadata.get("cert_domain_keywords") or ""))
    if q_domains and qual_domains and _overlap_ratio(q_domains, qual_domains) > 0:
        score += domain_bonus
    # 정규화도메인(상위 도메인) 또는 분야(main_field)·NCS 대분류가 겹치면 추가로 약한 가산
    if q_top_domain and qual_domains and _overlap_ratio(q_top_domain, qual_domains) > 0:
        score += domain_bonus * 0.5
    qual_main_tokens = qual_job
    if q_main_field and qual_main_tokens and _overlap_ratio(q_main_field, qual_main_tokens) > 0:
        score += job_bonus * 0.5
    if q_ncs and qual_main_tokens and _overlap_ratio(q_ncs, qual_main_tokens) > 0:
        score += job_bonus * 0.3
    # 질의 도메인 키워드 ↔ 자격증 domain_keywords 직접 매칭 (qual_vector 신호 반영)
    if q_domain_keywords and qual_domain_keywords and _overlap_ratio(q_domain_keywords, qual_domain_keywords) > 0:
        score += domain_keyword_bonus
    # 쿼리 도메인(IT·디지털 집중 vs 그 외) ↔ 자격 메타 도메인 불일치 감점
    if (
        query_is_it is not None
        and domain_mismatch_penalty != 0.0
        and qual_metadata.get("is_it") is not None
        and query_is_it != qual_metadata["is_it"]
    ):
        score += domain_mismatch_penalty
    return score


def fetch_qual_metadata_bulk(db: Session, qual_ids: List[int]) -> Dict[int, Dict[str, Any]]:
    """qual_id 목록에 대해 main_field, ncs_large, related_majors 조회."""
    if not qual_ids:
        return {}
    out: Dict[int, Dict[str, Any]] = {}
    try:
        rows = db.execute(
            text("SELECT qual_id, main_field, ncs_large FROM qualification WHERE qual_id = ANY(:ids)"),
            {"ids": qual_ids},
        ).fetchall()
        for r in rows:
            out[r.qual_id] = {
                "main_field": (r.main_field or "").strip(),
                "ncs_large": (r.ncs_large or "").strip(),
                "related_majors": [],
            }
        if out:
            maj_rows = db.execute(
                text("""
                    SELECT qual_id, major FROM major_qualification_map
                    WHERE qual_id = ANY(:ids) ORDER BY qual_id, score DESC
                """),
                {"ids": list(out.keys())},
            ).fetchall()
            by_qual: Dict[int, List[str]] = {}
            for r in maj_rows:
                by_qual.setdefault(r.qual_id, [])
                if len(by_qual[r.qual_id]) < 5:
                    by_qual[r.qual_id].append((r.major or "").strip())
            for qid, majors in by_qual.items():
                if qid in out:
                    raw_list = [m for m in majors if m]
                    out[qid]["related_majors"] = raw_list
                    # 자격증 메타데이터에도 전공 원본 + major_category(정규화)를 모두 보관
                    out[qid]["related_majors_normalized"] = [normalize_major(m) for m in raw_list]
        # certificates_vectors의 domain/domain_normalized를 함께 읽어, 도메인 기반 soft score 신호를 강화
        if out:
            vec_rows = db.execute(
                text(
                    """
                    SELECT qual_id, domain, domain_normalized, domain_keywords, metadata
                    FROM certificates_vectors
                    WHERE qual_id = ANY(:ids)
                      AND COALESCE(chunk_index, 0) = 0
                    """
                ),
                {"ids": list(out.keys())},
            ).fetchall()
            for r in vec_rows:
                if r.qual_id not in out:
                    continue
                out[r.qual_id]["cert_domain"] = (r.domain or "").strip()
                out[r.qual_id]["cert_top_domain"] = (r.domain_normalized or "").strip()
                out[r.qual_id]["cert_domain_keywords"] = (r.domain_keywords or "").strip()
                md = r.metadata if isinstance(r.metadata, dict) else {}
                if isinstance(md, dict):
                    main_fields = md.get("main_fields")
                    ncs_large_list = md.get("ncs_large")
                    if isinstance(main_fields, list):
                        out[r.qual_id]["main_fields"] = [
                            str(x).strip() for x in main_fields if str(x).strip()
                        ][:8]
                    if isinstance(ncs_large_list, list):
                        out[r.qual_id]["ncs_large_list"] = [
                            str(x).strip() for x in ncs_large_list if str(x).strip()
                        ][:8]
                # major_qualification_map에 없을 때는 qual_vector metadata.related_majors를 폴백으로 사용
                if not (out[r.qual_id].get("related_majors") or []):
                    md_maj = md.get("related_majors") if isinstance(md, dict) else None
                    if isinstance(md_maj, list):
                        cleaned = [str(m).strip() for m in md_maj if str(m).strip()]
                        if cleaned:
                            out[r.qual_id]["related_majors"] = cleaned[:5]
                            out[r.qual_id]["related_majors_normalized"] = [normalize_major(m) for m in cleaned[:5]]
        # IT·디지털 집중 플래그 및 넓은 도메인 플래그 (불일치 감점·도메인 보너스용)
        try:
            from app.rag.utils.domain_tokens import (
                get_it_tokens,
                get_non_it_tokens,
                detect_broad_domains_in_text,
            )
            it_tokens = get_it_tokens()
            non_it_tokens = get_non_it_tokens()
            for qid, meta in out.items():
                text_parts = " ".join(
                    [
                        str(meta.get("main_field") or ""),
                        str(meta.get("ncs_large") or ""),
                        str(meta.get("cert_domain") or ""),
                        str(meta.get("cert_top_domain") or ""),
                        str(meta.get("cert_domain_keywords") or ""),
                    ]
                    + [str(m) for m in (meta.get("related_majors") or [])]
                )
                is_it = None
                for t in it_tokens:
                    if t in text_parts:
                        is_it = True
                        break
                if is_it is None:
                    for t in non_it_tokens:
                        if t in text_parts:
                            is_it = False
                            break
                meta["is_it"] = is_it
                # 넓은 도메인(금융, 의료, 관광/서비스 등) 라벨
                meta["domains"] = detect_broad_domains_in_text(text_parts)
        except Exception:
            for meta in out.values():
                meta["is_it"] = None
                meta["domains"] = []
    except Exception:
        pass
    return out
