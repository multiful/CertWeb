"""
dataset/ncs_mapping1.csv → qualification.ncs_large_mapped, ncs_mid 적용.

- 자격증명 기준으로 DB qual_name 과 매칭 (공백·구두점 정규화 키).
- 동일 자격증명에 여러 CSV 행이 있으면:
  1) qualification.ncs_large(원본 DB, 수정 없음)와 대직무분류 정규화 일치·부분일치로 행 선택
  2) 불가 시 (대직무, 중직무) 조합 다수결, 동률이면 자격증ID 유무·ncsID 로 정렬

core qualification 컬럼(qual_name, main_field, ncs_large 등)은 변경하지 않고
ncs_large_mapped / ncs_mid 만 갱신한다.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Tuple

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.rag.utils.ncs_csv_mapping_resolve import (
    choose_ncs_payload_from_candidates,
    compact_key,
    load_ncs_mapping_csv_rows,
)


def parse_ncs_mapping_csv(path: str | Path) -> Dict[str, Tuple[str, str]]:
    """
    자격증명(원문) → (대직무분류, 중직무분류).
    DB 없이 파일만 쓸 때: 동일 이름은 다수결·자격증ID·ncsID 로 단일화.
    """
    rows = load_ncs_mapping_csv_rows(path)
    by_name: Dict[str, List[dict]] = {}
    for r in rows:
        name = (r.get("자격증명") or "").strip()
        if not name:
            continue
        by_name.setdefault(name, []).append(r)

    out: Dict[str, Tuple[str, str]] = {}
    for name, cands in by_name.items():
        lg, mid, _ = choose_ncs_payload_from_candidates(cands, db_ncs_large=None)
        out[name] = (lg, mid)
    return out


def apply_ncs_mapping_to_qualification(
    db: Session,
    csv_path: str | Path,
    *,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """
    qualification 전체를 스캔해 자격증명이 CSV와 일치하면 ncs_large_mapped, ncs_mid UPDATE.
    매칭 안 된 행은 기존 값 유지.
    """
    rows = load_ncs_mapping_csv_rows(csv_path)
    if not rows:
        return {"error": "empty_csv", "updated": 0, "matched_keys": 0}

    by_name: Dict[str, List[dict]] = {}
    for r in rows:
        name = (r.get("자격증명") or "").strip()
        if not name:
            continue
        by_name.setdefault(name, []).append(r)

    key_to_candidates: Dict[str, List[dict]] = {}
    for name, cands in by_name.items():
        k = compact_key(name)
        if k:
            key_to_candidates[k] = cands

    qrows = db.execute(
        text("SELECT qual_id, qual_name, ncs_large, main_field FROM qualification")
    ).fetchall()

    stats = {
        "csv_path": str(csv_path),
        "csv_distinct_names": len(by_name),
        "compact_keys": len(key_to_candidates),
        "pick_db_aligned": 0,
        "pick_main_field_hint": 0,
        "pick_plurality_only": 0,
        "pick_single_row": 0,
    }

    qual_updates: List[Tuple[int, str, str]] = []
    for r in qrows:
        qn = (r.qual_name or "").strip()
        k = compact_key(qn)
        if not k or k not in key_to_candidates:
            continue
        cands = key_to_candidates[k]
        db_ncs = (r.ncs_large or "").strip() or None
        db_mf = (r.main_field or "").strip() or None
        large, mid, how = choose_ncs_payload_from_candidates(
            cands, db_ncs_large=db_ncs, db_main_field=db_mf
        )
        if how == "db_ncs_large":
            stats["pick_db_aligned"] += 1
        elif how == "main_field_hint":
            stats["pick_main_field_hint"] += 1
        elif how == "plurality":
            stats["pick_plurality_only"] += 1
        else:
            stats["pick_single_row"] += 1
        qual_updates.append((int(r.qual_id), large[:200] if large else "", mid[:200] if mid else ""))

    updated = 0
    scanned = len(qrows)
    for qid, large, mid in qual_updates:
        if dry_run:
            updated += 1
            continue
        db.execute(
            text(
                """
                UPDATE qualification
                SET ncs_large_mapped = :large,
                    ncs_mid = :mid
                WHERE qual_id = :qid
                """
            ),
            {"qid": qid, "large": large or None, "mid": mid or None},
        )
        updated += 1

    if not dry_run:
        db.commit()

    stats.update(
        {
            "qual_rows_scanned": scanned,
            "qual_rows_updated": updated,
            "dry_run": dry_run,
        }
    )
    return stats
