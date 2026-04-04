"""
dataset/main_field_all.txt, dataset/ncs_large_all.txt 기반 허용 목록.
필터 옵션( main_field, ncs_large ) 검증·제한, 슬롯 검증 등에 사용.
"""
from pathlib import Path
from typing import FrozenSet

_root: Path | None = None
_main_field_set: FrozenSet[str] | None = None
_ncs_large_set: FrozenSet[str] | None = None


def _dataset_root() -> Path:
    global _root
    if _root is None:
        _root = Path(__file__).resolve().parents[3] / "dataset"
    return _root


def get_allowed_main_fields() -> FrozenSet[str]:
    """dataset/main_field_all.txt 한 줄씩(strip) 집합. 파일 없으면 빈 집합."""
    global _main_field_set
    if _main_field_set is not None:
        return _main_field_set
    p = _dataset_root() / "main_field_all.txt"
    if not p.is_file():
        _main_field_set = frozenset()
        return _main_field_set
    _main_field_set = frozenset(
        line.strip() for line in p.read_text(encoding="utf-8").splitlines() if line.strip()
    )
    return _main_field_set


def get_allowed_ncs_large() -> FrozenSet[str]:
    """dataset/ncs_large_all.txt 한 줄씩(strip) 집합. 파일 없으면 빈 집합."""
    global _ncs_large_set
    if _ncs_large_set is not None:
        return _ncs_large_set
    p = _dataset_root() / "ncs_large_all.txt"
    if not p.is_file():
        _ncs_large_set = frozenset()
        return _ncs_large_set
    _ncs_large_set = frozenset(
        line.strip() for line in p.read_text(encoding="utf-8").splitlines() if line.strip()
    )
    return _ncs_large_set


def filter_main_fields(candidates: list[str]) -> list[str]:
    """candidates 중 허용 목록에 있는 것만 반환. 허용 목록이 비어 있으면 candidates 그대로."""
    allowed = get_allowed_main_fields()
    if not allowed:
        return list(candidates)
    return [x for x in candidates if x and x in allowed]


def filter_ncs_large(candidates: list[str]) -> list[str]:
    """candidates 중 ncs_large_all.txt에 있는 것만 반환. 허용 목록이 비어 있으면 candidates 그대로."""
    allowed = get_allowed_ncs_large()
    if not allowed:
        return list(candidates)
    return [x for x in candidates if x and x in allowed]
