"""RAG 응답 Redis 캐시: query + filters + top_k + baseline_id 해시 키."""
from typing import Any, Optional

from app.redis_client import redis_client
from app.rag.config import get_rag_settings


def get_cached_rag_response(
    query: str,
    filters: Optional[dict] = None,
    top_k: int = 5,
    baseline_id: str = "current",
) -> Optional[Any]:
    """캐시에서 RAG 응답 조회."""
    key = redis_client.rag_ask_cache_key(query=query, filters=filters or {}, top_k=top_k, baseline_id=baseline_id)
    return redis_client.get(key)


def set_cached_rag_response(
    query: str,
    value: Any,
    filters: Optional[dict] = None,
    top_k: int = 5,
    baseline_id: str = "current",
    ttl: Optional[int] = None,
) -> bool:
    """RAG 응답 캐시 저장."""
    key = redis_client.rag_ask_cache_key(query=query, filters=filters or {}, top_k=top_k, baseline_id=baseline_id)
    ttl = ttl or get_rag_settings().RAG_CACHE_TTL
    return redis_client.set(key, value, ttl=ttl)
