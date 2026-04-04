"""
Indexing_opt §8: 파서/인제스트 실패 건을 로컬 DLQ(JSONL)에 적재.
외부 큐 없이 운영·재처리 추적용 최소 구현(추가 인프라 비용 없음).
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

_DLQ_PATH = Path(__file__).resolve().parents[3] / "data" / "ingest_dlq.jsonl"


def append_ingest_dlq(
    *,
    stage: str,
    qual_id: Optional[Any] = None,
    source_path: Optional[str] = None,
    detail: Optional[Dict[str, Any]] = None,
) -> None:
    """한 줄 JSONL append. 실패해도 상위 파이프라인은 중단하지 않음."""
    try:
        _DLQ_PATH.parent.mkdir(parents=True, exist_ok=True)
        rec = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "stage": stage,
            "qual_id": qual_id,
            "source_path": source_path,
            "detail": detail or {},
        }
        with open(_DLQ_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except Exception:
        logger.exception("ingest_dlq append failed: stage=%s qual_id=%s", stage, qual_id)
