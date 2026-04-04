"""
Pre-retrieval 관측용 §2 스키마에 가까운 구조화 trace (문서: dataset/opt_Pre-retrieval.md).
플래그 RAG_PRE_RETRIEVAL_TRACE_ENABLE 시 hybrid_retrieve에서 JSON 한 줄 로그 출력.
"""
from __future__ import annotations

import json
import logging
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class PreRetrievalTrace(BaseModel):
    """Retriever 직전까지 채울 수 있는 필드 위주 (semantic cache·OOS 등은 별도)."""

    original_query: str = ""
    normalized_query: str = ""  # dense / 구조화 재질의 결과
    query_language: str = "und"  # BCP-47 근사 (pre_retrieval_signals)
    query_type: str = ""
    intent_label: Optional[str] = None  # query_type과 동일 계열로 둠
    intent_confidence: Optional[float] = None  # 0.0~1.0, 규칙 기반 휴리스틱
    difficulty_label: Optional[str] = None  # easy | medium | hard
    difficulty_confidence: Optional[float] = None
    latency_breakdown_ms: Dict[str, Any] = Field(default_factory=dict)
    strategy_flags: Dict[str, Any] = Field(default_factory=dict)
    budget_remaining_ms: Optional[float] = None
    budget_deadline_set: bool = False
    skip_expansion_identifier_heavy: bool = False
    identifier_heavy: bool = False
    # True: (1) Redis hybrid 결과 캐시 히트 RAG_RETRIEVAL_RESULT_CACHE_ENABLE 또는 (2) 추후 ANN 의미 캐시
    cache_hit_semantic: Optional[bool] = False
    vector_search_meta: Dict[str, Any] = Field(default_factory=dict)
    rewrite_skipped: bool = False
    rewrite_skip_reason: Optional[str] = None  # identifier_heavy | budget_ms_below_min_for_rewrite

    def as_log_dict(self) -> Dict[str, Any]:
        return self.model_dump()


def log_pre_retrieval_trace(trace: PreRetrievalTrace, *, query_snippet_len: int = 200) -> None:
    """민감도 완화: 질의는 앞부분만."""
    d = trace.as_log_dict()
    oq = d.get("original_query") or ""
    if isinstance(oq, str) and len(oq) > query_snippet_len:
        d["original_query"] = oq[:query_snippet_len] + "…"
    nq = d.get("normalized_query") or ""
    if isinstance(nq, str) and len(nq) > query_snippet_len:
        d["normalized_query"] = nq[:query_snippet_len] + "…"
    try:
        logger.info("pre_retrieval_trace %s", json.dumps(d, ensure_ascii=False))
    except Exception as e:
        logger.debug("pre_retrieval_trace log failed: %s", e)
