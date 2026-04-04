"""
Pre-retrieval 가이드(§2 출력 스키마·§17 난이도)에 맞춘 경량 휴리스틱.
LLM 호출 없이 query 문자열만으로 언어·난이도·의도 신뢰도 보조값을 채운다.
"""
from __future__ import annotations

import re
import time
from typing import Any, Dict, Optional, Tuple


def detect_query_language(query: str) -> str:
    """BCP-47 근사: 한국어 비중이 높으면 ko, 라틴 알파벳 위주면 en, 그 외 und."""
    q = (query or "").strip()
    if not q:
        return "und"
    hangul = len(re.findall(r"[\uac00-\ud7a3]", q))
    latin = len(re.findall(r"[A-Za-z]", q))
    total = hangul + latin
    if total == 0:
        return "und"
    if hangul / total >= 0.25:
        return "ko"
    if latin / total >= 0.6:
        return "en"
    return "und"


def estimate_query_difficulty(query: str) -> Tuple[str, float]:
    """
    토큰 길이 기반 난이도(§17 참고용 휴리스틱).
    반환: (easy|medium|hard, 0.0~1.0 confidence)
    """
    tokens = [t for t in (query or "").strip().split() if t]
    n = len(tokens)
    if n <= 4:
        return "easy", 0.72
    if n <= 16:
        return "medium", 0.68
    return "hard", 0.62


_INTENT_CONFIDENCE_BY_TYPE: Dict[str, float] = {
    "keyword": 0.74,
    "natural": 0.80,
    "mixed": 0.58,
    "cert_name_included": 0.82,
    "major+job": 0.76,
    "roadmap": 0.70,
}


def intent_confidence_for_query_type(query_type: Optional[str]) -> float:
    """규칙/슬롯 기반 query_type에 대한 보수적 신뢰도(가이드 §2 confidence 스케일)."""
    qt = (query_type or "").strip()
    if not qt:
        return 0.65
    return float(_INTENT_CONFIDENCE_BY_TYPE.get(qt, 0.70))


def pre_retrieval_aux_fields(
    query: str,
    query_type: str,
    *,
    t_pre_start: float,
    latency_key: str = "to_fusion_ms",
) -> Dict[str, Any]:
    """PreRetrievalTrace에 병합할 보조 필드."""
    elapsed_ms = round(max(0.0, (time.monotonic() - t_pre_start) * 1000.0), 2)
    diff_label, diff_conf = estimate_query_difficulty(query)
    return {
        "query_language": detect_query_language(query),
        "difficulty_label": diff_label,
        "difficulty_confidence": diff_conf,
        "intent_confidence": intent_confidence_for_query_type(query_type),
        "latency_breakdown_ms": {latency_key: elapsed_ms},
    }
