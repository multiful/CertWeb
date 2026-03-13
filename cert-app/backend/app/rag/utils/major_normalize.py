"""
전공(major) 문자열 정규화 유틸.

- data/major_normalize.json 은 Supabase major 테이블에서 export한
  major_name → major_category 매핑만 사용 (equals 규칙만 적용).
- contains/prefix/regex 규칙은 사용하지 않음.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, TypedDict


class MajorRule(TypedDict, total=False):
    pattern: str
    normalized: str
    kind: str


_RULES_CACHE: List[MajorRule] | None = None


def _rules_path() -> Path:
    try:
        from app.rag.config import get_rag_index_dir  # type: ignore

        base = get_rag_index_dir().parent  # data/
    except Exception:
        base = Path("data")
    return base / "major_normalize.json"


def _load_rules() -> List[MajorRule]:
    global _RULES_CACHE
    if _RULES_CACHE is not None:
        return _RULES_CACHE

    path = _rules_path()
    rules: List[MajorRule] = []
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            raw = data.get("rules") or []
            for item in raw:
                if not isinstance(item, dict):
                    continue
                kind = (item.get("kind") or "").strip().lower()
                if kind != "equals":
                    continue
                pattern = str(item.get("pattern") or "").strip()
                normalized = str(item.get("normalized") or "").strip()
                if not pattern or not normalized:
                    continue
                rules.append(MajorRule(pattern=pattern, normalized=normalized, kind="equals"))
        except Exception:
            rules = []

    _RULES_CACHE = rules
    return _RULES_CACHE


def normalize_major(major: str) -> str:
    """
    전공 문자열을 Supabase major 테이블 기준으로 정규화 (major_name → major_category).
    equals 규칙만 사용하므로, 테이블에 없는 전공명은 그대로 반환.
    """
    text = (major or "").strip()
    if not text:
        return text

    rules = _load_rules()
    for rule in rules:
        if text == rule["pattern"]:
            return rule["normalized"]
    return text

