"""
Profile-aware golden: JSONL 행에서 user_profile 구성.
query_text, major, grade_level, favorite_cert_names, acquired_cert_names(또는 acquired_qual_ids), expected_certs 지원.
기존 reco 골든(profile 필드 없음)과 혼용 가능.
"""
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session
from sqlalchemy import text

from app.rag.utils.dense_query_rewrite import UserProfile
from app.rag.eval.reco_golden import _qual_id_to_name_map, _cert_name_to_qual_ids


def row_has_profile(row: Dict[str, Any]) -> bool:
    """이 행에 프로필 정보가 하나라도 있으면 True."""
    return bool(
        row.get("major")
        or row.get("grade_level") is not None
        or (row.get("favorite_cert_names") and len(row.get("favorite_cert_names", [])) > 0)
        or (row.get("acquired_cert_names") and len(row.get("acquired_cert_names", [])) > 0)
        or (row.get("acquired_qual_ids") and len(row.get("acquired_qual_ids", [])) > 0)
    )


def build_user_profile_from_row(
    row: Dict[str, Any],
    db: Session,
    qual_id_to_name: Optional[Dict[int, str]] = None,
) -> Optional[UserProfile]:
    """
    profile-aware golden 행에서 hybrid_retrieve에 넘길 user_profile 구성.
    프로필 필드가 없거나 비어 있으면 None 반환 (기존 경로 유지).
    """
    if not row_has_profile(row):
        return None

    if qual_id_to_name is None:
        qual_id_to_name = _qual_id_to_name_map(db)

    profile: UserProfile = {}

    major = (row.get("major") or "").strip()
    if major:
        profile["major"] = major

    grade_level = row.get("grade_level")
    if grade_level is not None:
        try:
            g = int(grade_level)
            if 1 <= g <= 4:
                profile["grade_level"] = g
        except (TypeError, ValueError):
            pass

    favorite_cert_names = row.get("favorite_cert_names") or []
    if isinstance(favorite_cert_names, list) and favorite_cert_names:
        profile["favorite_cert_names"] = [str(c).strip() for c in favorite_cert_names if c][:10]
        # favorite_field_tokens: 해당 자격증의 main_field, ncs_large 수집
        fav_qual_ids: List[int] = []
        for name in profile["favorite_cert_names"]:
            fav_qual_ids.extend(_cert_name_to_qual_ids(name, qual_id_to_name))
        fav_qual_ids = list(dict.fromkeys(fav_qual_ids))[:20]
        if fav_qual_ids:
            rows_f = db.execute(
                text("SELECT qual_id, main_field, ncs_large FROM qualification WHERE qual_id = ANY(:ids)"),
                {"ids": fav_qual_ids},
            ).fetchall()
            tokens: List[str] = []
            for r in rows_f:
                for fld in (getattr(r, "main_field", None), getattr(r, "ncs_large", None)):
                    if fld and str(fld).strip():
                        tokens.append(str(fld).strip())
            if tokens:
                profile["favorite_field_tokens"] = list(dict.fromkeys(tokens))[:20]

    acquired_qual_ids: List[int] = list(row.get("acquired_qual_ids") or [])
    if not acquired_qual_ids and row.get("acquired_cert_names"):
        acq_names = row.get("acquired_cert_names")
        if isinstance(acq_names, list):
            for name in acq_names:
                acquired_qual_ids.extend(_cert_name_to_qual_ids(str(name).strip(), qual_id_to_name))
            acquired_qual_ids = list(dict.fromkeys(acquired_qual_ids))
    if acquired_qual_ids:
        profile["acquired_qual_ids"] = acquired_qual_ids[:50]

    return profile if profile else None
