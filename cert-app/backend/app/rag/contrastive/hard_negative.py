"""
Hard negative 후보 생성 규칙 (추천형 자격증 도메인).
- 같은 취업 목적이지만 직무 축이 다름
- 데이터 계열처럼 보이지만 희망직무와 거리가 있음
- 일반 사무/공통 자격증처럼 연관은 있으나 핵심 추천은 아님
"""
from typing import List, Set

from sqlalchemy.orm import Session
from sqlalchemy import text


def get_qual_fields_map(db: Session) -> dict[int, dict]:
    """qual_id -> {main_field, ncs_large} 맵."""
    rows = db.execute(text("""
        SELECT qual_id, main_field, ncs_large FROM qualification WHERE is_active = TRUE
    """)).fetchall()
    return {
        r.qual_id: {"main_field": (r.main_field or "").strip(), "ncs_large": (r.ncs_large or "").strip()}
        for r in rows
    }


def select_hard_negatives(
    db: Session,
    positive_qual_ids: List[int],
    all_qual_ids: List[int],
    qual_fields: dict[int, dict],
    max_per_sample: int = 5,
) -> List[int]:
    """
    positive와 겹치지 않는 qual_id 중에서 hard negative 후보 선택.
    규칙 1: positive와 같은 main_field를 가진 다른 자격증 (같은 분야, 다른 자격)
    규칙 2: positive와 같은 ncs_large를 가진 다른 자격증
    규칙 3: 그 외 나머지에서 랜덤에 가깝게 일부 (연관 있으나 핵심 아님)
    """
    pos_set = set(positive_qual_ids)
    candidates: List[int] = []
    main_fields_of_pos = set()
    ncs_of_pos = set()
    for qid in positive_qual_ids:
        f = qual_fields.get(qid) or {}
        if f.get("main_field"):
            main_fields_of_pos.add(f["main_field"])
        if f.get("ncs_large"):
            ncs_of_pos.add(f["ncs_large"])

    for qid in all_qual_ids:
        if qid in pos_set:
            continue
        f = qual_fields.get(qid) or {}
        mf, ncs = f.get("main_field") or "", f.get("ncs_large") or ""
        if mf in main_fields_of_pos or ncs in ncs_of_pos:
            candidates.append(qid)
    if len(candidates) <= max_per_sample:
        return candidates[:max_per_sample]
    return candidates[:max_per_sample]
