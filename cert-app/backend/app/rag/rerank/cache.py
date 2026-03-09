"""
Reranker Pair 캐싱: (query, document) 조합에 대한 score를 캐싱하여 API 호출 감소.

- In-memory LRU 캐시 (추후 Redis 확장 가능하도록 인터페이스 분리)
- TTL 기반 만료
- cache hit/miss 통계 제공
"""
import hashlib
import threading
import time
from collections import OrderedDict
from typing import Dict, List, Optional, Tuple, Any

from app.redis_client import redis_client
from app.rag.config import get_rag_settings


class RerankerCache:
    """
    Thread-safe LRU 캐시 (query, doc_hash) -> score.
    
    사용 예:
        cache = RerankerCache(max_size=10000, ttl_seconds=3600)
        
        # 캐시 조회
        cached = cache.get_many(query, doc_hashes)
        # cached: {doc_hash: score} for hits
        
        # miss 항목만 API 호출 후 저장
        cache.set_many(query, {doc_hash: score, ...})
    """
    
    def __init__(self, max_size: int = 10000, ttl_seconds: int = 3600, version: str = "v1"):
        self._cache: OrderedDict[str, Tuple[float, float]] = OrderedDict()  # key -> (score, timestamp)
        self._max_size = max_size
        self._ttl = ttl_seconds
        self._version = version
        self._lock = threading.Lock()
        self._hits = 0
        self._misses = 0
    
    @staticmethod
    def _make_key(query: str, doc_hash: str) -> str:
        """로컬 캐시 키 생성: query + doc_hash를 SHA256으로 해싱."""
        combined = f"{query}|||{doc_hash}"
        return hashlib.sha256(combined.encode("utf-8")).hexdigest()[:32]
    
    @staticmethod
    def hash_document(content: str) -> str:
        """문서 내용을 해시로 변환."""
        return hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]

    def _redis_key(self, query: str, doc_hash: str) -> str:
        """Redis 캐시 키: 버전 prefix + 해시."""
        # 모델/Space 버전 변경 시 prefix만 올려서 전체 무효화
        prefix = f"rerank:{self._version}"
        base = f"{(query or '').strip()}|||{doc_hash}"
        h = hashlib.sha256(base.encode("utf-8")).hexdigest()[:32]
        return f"{prefix}:{h}"
    
    def get(self, query: str, doc_hash: str) -> Optional[float]:
        """단일 항목 조회. None이면 miss. (로컬 LRU → Redis 순서로 조회)."""
        key = self._make_key(query, doc_hash)
        now = time.time()

        # 1) 로컬 LRU
        with self._lock:
            if key in self._cache:
                score, timestamp = self._cache[key]
                if now - timestamp <= self._ttl:
                    self._cache.move_to_end(key)
                    self._hits += 1
                    return score
                # TTL 만료
                del self._cache[key]

        # 2) Redis
        redis_key = self._redis_key(query, doc_hash)
        cached = redis_client.get(redis_key)
        if isinstance(cached, (int, float)):
            score = float(cached)
        elif isinstance(cached, dict) and "score" in cached:
            # 혹시 모를 포맷 확장 대비
            score = float(cached["score"])
        else:
            with self._lock:
                self._misses += 1
            return None

        # Redis hit → 로컬 LRU에 재적재
        with self._lock:
            self._cache[key] = (score, now)
            self._cache.move_to_end(key)
            while len(self._cache) > self._max_size:
                self._cache.popitem(last=False)
            self._hits += 1
        return score
    
    def get_many(self, query: str, doc_hashes: List[str]) -> Dict[str, float]:
        """여러 항목 조회. {doc_hash: score} for hits only."""
        result = {}
        for dh in doc_hashes:
            score = self.get(query, dh)
            if score is not None:
                result[dh] = score
        return result
    
    def set(self, query: str, doc_hash: str, score: float) -> None:
        """단일 항목 저장. 로컬 LRU + Redis 모두에 기록."""
        key = self._make_key(query, doc_hash)
        now = time.time()
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
            self._cache[key] = (score, now)
            # LRU eviction
            while len(self._cache) > self._max_size:
                self._cache.popitem(last=False)

        # Redis에도 기록 (단일 float만 저장)
        try:
            redis_key = self._redis_key(query, doc_hash)
            redis_client.set(redis_key, float(score), ttl=self._ttl)
        except Exception:
            # Redis 장애 시에는 조용히 무시 (로컬 캐시만 사용)
            pass
    
    def set_many(self, query: str, scores: Dict[str, float]) -> None:
        """여러 항목 저장. scores: {doc_hash: score}"""
        for doc_hash, score in scores.items():
            self.set(query, doc_hash, score)
    
    def clear(self) -> None:
        """캐시 전체 삭제."""
        with self._lock:
            self._cache.clear()
            self._hits = 0
            self._misses = 0
    
    def stats(self) -> Dict[str, any]:
        """캐시 통계 반환."""
        with self._lock:
            total = self._hits + self._misses
            hit_rate = (self._hits / total * 100) if total > 0 else 0.0
            return {
                "size": len(self._cache),
                "max_size": self._max_size,
                "ttl_seconds": self._ttl,
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate_percent": round(hit_rate, 2),
            }


# 전역 싱글턴 인스턴스
_reranker_cache: Optional[RerankerCache] = None
_cache_lock = threading.Lock()


def get_reranker_cache(max_size: int = 10000, ttl_seconds: int = 3600) -> RerankerCache:
    """전역 캐시 인스턴스 반환 (싱글턴)."""
    global _reranker_cache
    with _cache_lock:
        if _reranker_cache is None:
            # 버전은 RAG_RERANKER_API_URL / 모델 변경 시 올려주기 위해 설정에서 가져오되,
            # env에 없으면 기본 v1 사용.
            version = "v1"
            try:
                settings = get_rag_settings()
                # 예: SPACE 리포 버전 등을 반영할 수 있도록 prefix만 지정
                if getattr(settings, "RAG_RERANKER_SPACE_REPO_ID", None):
                    version = "v1"
            except Exception:
                pass
            _reranker_cache = RerankerCache(max_size=max_size, ttl_seconds=ttl_seconds, version=version)
        return _reranker_cache


def reset_reranker_cache() -> None:
    """전역 캐시 초기화 (테스트용)."""
    global _reranker_cache
    with _cache_lock:
        if _reranker_cache is not None:
            _reranker_cache.clear()
            _reranker_cache = None
