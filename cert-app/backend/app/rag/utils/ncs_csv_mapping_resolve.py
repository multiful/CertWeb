"""ncs_mapping CSV 다행 → 단일 (대직무, 중직무) 선택 (DB ncs_large / main_field 정렬 + 다수결)."""
from __future__ import annotations

import csv
import re
from collections import Counter
from pathlib import Path
from typing import Dict, List, Literal, Optional, Tuple

How = Literal["single", "db_ncs_large", "main_field_hint", "plurality"]

# ncs_mapping1.csv 하단에 동일 직무(어촌개발·직무코드 2444)가 오염으로 반복된 행 식별용
_SPURIOUS_FISHERY_BOILERPLATE = "여행상품 개발자,총무 사무원,대기환경기술자"
_FISHERY_NAME_RE = re.compile(
    r"(수산|수산양식|어업|어로|해양|잠수|어부|해녀|어촌|양식기사|양식기능|양식산업|"
    r"수산양식기사|수산양식산업|어업생산|해양조사)",
)


def filter_spurious_fishery_boilerplate_rows(candidates: List[dict]) -> List[dict]:
    """
    직업 문구가 어촌개발 보일러플레이트인데 자격증명이 수산·어업 계열이 아니면 후보에서 제외.
    (원천 CSV 끝단 오염 행이 다수결·ncsID 우선에서 승리하는 것 방지)
    """
    if len(candidates) <= 1:
        return candidates
    out: List[dict] = []
    for r in candidates:
        job = (r.get("직업") or "").strip()
        if _SPURIOUS_FISHERY_BOILERPLATE in job:
            name = (r.get("자격증명") or "").strip()
            if not _FISHERY_NAME_RE.search(name):
                continue
        out.append(r)
    return out if out else candidates


def compact_key(s: str) -> str:
    if not s:
        return ""
    return re.sub(r"[\s\.・·,]+", "", (s or "").strip())


def load_ncs_mapping_csv_rows(path: str | Path) -> List[dict]:
    p = Path(path)
    if not p.is_file():
        return []
    with p.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def row_large_mid(r: dict) -> Tuple[str, str]:
    lg = (r.get("대직무분류") or "").strip().replace(".", "·")
    mid = (r.get("중직무분류") or "").strip().replace(".", "·")
    return lg, mid


def ncs_id_int(r: dict) -> int:
    try:
        return int((r.get("ncsID") or "0").strip() or 0)
    except ValueError:
        return 10**9


def cert_id_sort_key(r: dict) -> Tuple[int, int]:
    """다수결 동률 시: 자격증ID 유무 우선, ncsID 큰 행 우선(최근 보정본 선호)."""
    has = 0 if (r.get("자격증ID") or "").strip() else 1
    return (has, -ncs_id_int(r))


def _pick_by_signal_compact(
    candidates: List[dict], signal_raw: Optional[str]
) -> Optional[Tuple[str, str]]:
    """signal( DB ncs_large 또는 main_field )와 CSV 대직무분류 compact 일치·부분일치."""
    if not signal_raw or not candidates:
        return None
    sig = compact_key(signal_raw.replace(".", "·"))
    if not sig:
        return None
    best_pair: Optional[Tuple[str, str]] = None
    best_key: Optional[Tuple[int, int, int]] = None
    for r in candidates:
        lg, mid = row_large_mid(r)
        cl = compact_key(lg)
        if cl == sig:
            tier = 0
        elif cl and sig and (cl in sig or sig in cl):
            tier = 1
        else:
            tier = 2
        has_cert = 1 if (r.get("자격증ID") or "").strip() else 0
        nid = ncs_id_int(r)
        k = (tier, -has_cert, -nid)
        if best_key is None or k < best_key:
            best_key = k
            best_pair = (lg, mid)
    assert best_pair is not None and best_key is not None
    if best_key[0] < 2:
        return best_pair
    return None


def choose_ncs_payload_from_candidates(
    candidates: List[dict],
    *,
    db_ncs_large: Optional[str],
    db_main_field: Optional[str] = None,
) -> Tuple[str, str, How]:
    if not candidates:
        return "", "", "single"
    candidates = filter_spurious_fishery_boilerplate_rows(candidates)
    if not candidates:
        return "", "", "single"
    if len(candidates) == 1:
        lg, mid = row_large_mid(candidates[0])
        return lg, mid, "single"

    hit = _pick_by_signal_compact(candidates, db_ncs_large)
    if hit:
        return hit[0], hit[1], "db_ncs_large"

    hit = _pick_by_signal_compact(candidates, db_main_field)
    if hit:
        return hit[0], hit[1], "main_field_hint"

    pairs = [row_large_mid(r) for r in candidates]
    cnt = Counter(pairs)
    top_freq = cnt.most_common(1)[0][1]
    winners = [p for p, c in cnt.items() if c == top_freq]
    if len(winners) == 1:
        lg, mid = winners[0]
        return lg, mid, "plurality"

    tied_rows = [r for r in candidates if row_large_mid(r) in winners]
    tied_rows.sort(key=lambda r: cert_id_sort_key(r))
    lg, mid = row_large_mid(tied_rows[0])
    return lg, mid, "plurality"
