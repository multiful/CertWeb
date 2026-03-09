"""
Metadata 기반 soft scoring: 직무/전공/추천대상 일치 시 가산, 분야 이탈 시 감점.
IT↔비IT 도메인 불일치 시 감점(선택, RAG_METADATA_DOMAIN_MISMATCH_ENABLE).
"""
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session
from sqlalchemy import text


# 기본 가중치 (config로 오버라이드)
DEFAULT_JOB_BONUS = 0.15
DEFAULT_MAJOR_BONUS = 0.10
DEFAULT_TARGET_BONUS = 0.10
DEFAULT_FIELD_PENALTY = -0.20
DEFAULT_DOMAIN_MISMATCH_PENALTY = -0.35


def _normalize_tokens(s: str) -> set:
    """공백/쉼표 분리, 소문자 없음(한글)."""
    if not s or not isinstance(s, str):
        return set()
    return set(t.strip() for t in s.replace(",", " ").split() if t.strip())


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
    query_slots: rewrite에서 추출한 전공, 희망직무, 목적, 관심분야 등.
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

    score = 0.0
    q_job = _normalize_tokens(str(query_slots.get("희망직무") or query_slots.get("관심분야") or ""))
    q_major = _normalize_tokens(str(query_slots.get("전공") or ""))
    q_interest = _normalize_tokens(str(query_slots.get("관심분야") or ""))

    qual_job = _normalize_tokens(str(qual_metadata.get("main_field") or "") + " " + str(qual_metadata.get("ncs_large") or ""))
    qual_majors = qual_metadata.get("related_majors") or []
    if isinstance(qual_majors, list):
        qual_major_set = set()
        for m in qual_majors:
            qual_major_set |= _normalize_tokens(str(m))
    else:
        qual_major_set = _normalize_tokens(str(qual_majors))

    if q_job and qual_job and _overlap_ratio(q_job, qual_job) > 0:
        score += job_bonus
    if q_major and qual_major_set and _overlap_ratio(q_major, qual_major_set) > 0:
        score += major_bonus
    if q_interest and qual_job and _overlap_ratio(q_interest, qual_job) > 0:
        score += target_bonus * 0.5
    if q_job and qual_job and len(qual_job) > 0 and _overlap_ratio(q_job, qual_job) == 0 and len(q_job) >= 2:
        score += field_penalty * 0.5
    # IT↔비IT 도메인 불일치 감점 (쿼리 IT인데 자격증 비IT, 또는 그 반대)
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
                    out[qid]["related_majors"] = [m for m in majors if m]
        # IT/비IT 도메인 플래그 (도메인 불일치 감점용)
        try:
            from app.rag.utils.domain_tokens import get_it_tokens, get_non_it_tokens
            it_tokens = get_it_tokens()
            non_it_tokens = get_non_it_tokens()
            for qid, meta in out.items():
                text_parts = " ".join([
                    str(meta.get("main_field") or ""),
                    str(meta.get("ncs_large") or ""),
                ] + [str(m) for m in (meta.get("related_majors") or [])])
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
        except Exception:
            for meta in out.values():
                meta["is_it"] = None
    except Exception:
        pass
    return out
