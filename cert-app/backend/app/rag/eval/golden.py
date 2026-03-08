"""
골든셋 로드: JSONL 파일을 읽어 평가용 리스트 반환.
reco 형식(query_text, expected_certs 등)은 common.normalize_gold_labels에서 정규화.
"""
import json
from pathlib import Path
from typing import Any, Dict, List


def load_golden(golden_path: str) -> List[Dict[str, Any]]:
    """
    JSONL 골든 파일을 읽어 행 단위 dict 리스트 반환.
    """
    path = Path(golden_path)
    if not path.exists():
        return []
    out: List[Dict[str, Any]] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return out
