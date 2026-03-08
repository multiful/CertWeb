"""골든셋 JSONL 로더: id, question, expected_answer, gold_chunk_ids, tags, filters."""
import json
from pathlib import Path
from typing import Any, Dict, List, Optional


def load_golden(path: str) -> List[Dict[str, Any]]:
    """
    JSONL 한 줄당: id, question, expected_answer(optional), gold_chunk_ids(list), tags, filters(optional)
    """
    out = []
    p = Path(path)
    if not p.exists():
        return out
    with open(p, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return out
