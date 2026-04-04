"""
동일 질의에 대한 hybrid_retrieve 최종 후보(리랭커 비활성 시) Redis 캐시.
opt_Pre-retrieval §16에 대응하는 경량 레이어 — 개인화·필터·리랭커 사용 시 비활성.
"""
from __future__ import annotations

import hashlib
import logging
from typing import Any, Dict, List, Optional, Tuple

from app.rag.config import get_rag_settings
from app.redis_client import redis_client

logger = logging.getLogger(__name__)

_PREFIX = "rag:hybrid:result:v1:"


def _settings_fingerprint() -> str:
    s = get_rag_settings()
    parts = [
        str(getattr(s, "RAG_FUSION_METHOD", "linear")),
        str(getattr(s, "RAG_TOP_N_CANDIDATES", "")),
        str(getattr(s, "RAG_RRF_K", "")),
        str(getattr(s, "RAG_CONTRASTIVE_ENABLE", "")),
        str(getattr(s, "RAG_METADATA_SOFT_SCORE_ENABLE", "")),
        str(getattr(s, "RAG_VECTOR_THRESHOLD", "")),
        str(getattr(s, "RAG_DENSE_USE_QUERY_REWRITE", "")),
        str(getattr(s, "RAG_CHANNEL_CONTEXTUAL_PROMPT_ENABLE", "")),
        str(getattr(s, "RAG_CHANNEL_CONTEXTUAL_PROMPT_APPLY_BM25", "")),
        str(getattr(s, "RAG_PERSONALIZED_SOFT_SCORE_ENABLE", "")),
        str(getattr(s, "RAG_HIERARCHICAL_RETRIEVAL_ENABLE", "")),
        str(getattr(s, "RAG_HIERARCHICAL_BLEND_WEIGHT", "")),
        str(getattr(s, "RAG_RRF_W_CONTRASTIVE768", "")),
        str(getattr(s, "RAG_BM25_TOP_N", "")),
        str(getattr(s, "RAG_CONTRASTIVE_TOP_N", "")),
    ]
    raw = "|".join(parts)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def eligible_for_retrieval_cache(
    *,
    filters: Optional[Dict[str, Any]],
    user_profile: Any,
    channels_override: Optional[List[str]],
    use_reranker: Optional[bool],
) -> bool:
    s = get_rag_settings()
    if not getattr(s, "RAG_RETRIEVAL_RESULT_CACHE_ENABLE", False):
        return False
    if not redis_client.is_connected():
        return False
    if filters:
        return False
    if user_profile is not None:
        return False
    if channels_override:
        return False
    will_rerank = use_reranker if use_reranker is not None else getattr(
        s, "RAG_USE_CROSS_ENCODER_RERANKER", False
        )
    if will_rerank:
        return False
    return True


def make_cache_key(
    query: str,
    top_k: int,
    top_n_candidates: int,
) -> str:
    q = (query or "").strip()
    fp = _settings_fingerprint()
    raw = f"{q}|{top_k}|{top_n_candidates}|{fp}"
    h = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    return _PREFIX + h


def get_cached_result(key: str) -> Optional[List[Tuple[str, float]]]:
    try:
        data = redis_client.get(key)
        if not data or not isinstance(data, list):
            return None
        out: List[Tuple[str, float]] = []
        for row in data:
            if isinstance(row, (list, tuple)) and len(row) >= 2:
                out.append((str(row[0]), float(row[1])))
        return out if out else None
    except Exception as e:
        logger.debug("retrieval cache get failed: %s", e)
        return None


def set_cached_result(
    key: str,
    candidates: List[Tuple[str, float]],
    ttl_seconds: int,
) -> None:
    try:
        payload = [[c[0], c[1]] for c in candidates]
        redis_client.set(key, payload, ttl=ttl_seconds)
    except Exception as e:
        logger.debug("retrieval cache set failed: %s", e)
