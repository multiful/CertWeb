"""NCS 매핑 CSV 경로. DB가 우선: resolved 스냅샷이 있으면 apply·평가 기본값으로 사용."""
from __future__ import annotations

from pathlib import Path

# app/rag/utils → cert-app/backend
_BACKEND_ROOT = Path(__file__).resolve().parents[3]

DATASET_DIR = _BACKEND_ROOT / "dataset"
NCS_CSV_RAW = DATASET_DIR / "ncs_mapping1.csv"
NCS_CSV_RESOLVED = DATASET_DIR / "ncs_mapping_resolved.csv"


def default_ncs_csv_path() -> Path:
    """
    qualification.ncs_large_mapped 반영용 기본 파일.

    - `ncs_mapping_resolved.csv` 가 있으면 사용 (자격증명당 1행, export 스크립트가
      DB `ncs_large`·`main_field` + 원본 CSV 규칙으로 생성).
    - 없으면 `ncs_mapping1.csv` (다행; apply 시 동일 규칙으로 행 선택).
    """
    if NCS_CSV_RESOLVED.is_file():
        return NCS_CSV_RESOLVED
    return NCS_CSV_RAW
