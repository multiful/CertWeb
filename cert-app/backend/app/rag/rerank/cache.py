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
from typing import Dict, List, Optional, Tuple


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
    
    def __init__(self, max_size: int = 10000, ttl_seconds: int = 3600):
        self._cache: OrderedDict[str, Tuple[float, float]] = OrderedDict()  # key -> (score, timestamp)
        self._max_size = max_size
        self._ttl = ttl_seconds
        self._lock = threading.Lock()
        self._hits = 0
        self._misses = 0
    
    @staticmethod
    def _make_key(query: str, doc_hash: str) -> str:
        """캐시 키 생성: query + doc_hash를 SHA256으로 해싱."""
        combined = f"{query}|||{doc_hash}"
        return hashlib.sha256(combined.encode("utf-8")).hexdigest()[:32]
    
    @staticmethod
    def hash_document(content: str) -> str:
        """문서 내용을 해시로 변환."""
        return hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]
    
    def get(self, query: str, doc_hash: str) -> Optional[float]:
        """단일 항목 조회. None이면 miss."""
        key = self._make_key(query, doc_hash)
        with self._lock:
            if key not in self._cache:
                self._misses += 1
                return None
            
            score, timestamp = self._cache[key]
            if time.time() - timestamp > self._ttl:
                del self._cache[key]
                self._misses += 1
                return None
            
            # LRU: 조회 시 맨 뒤로 이동
            self._cache.move_to_end(key)
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
        """단일 항목 저장."""
        key = self._make_key(query, doc_hash)
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
            self._cache[key] = (score, time.time())
            
            # LRU eviction
            while len(self._cache) > self._max_size:
                self._cache.popitem(last=False)
    
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
            _reranker_cache = RerankerCache(max_size=max_size, ttl_seconds=ttl_seconds)
        return _reranker_cache


def reset_reranker_cache() -> None:
    """전역 캐시 초기화 (테스트용)."""
    global _reranker_cache
    with _cache_lock:
        if _reranker_cache is not None:
            _reranker_cache.clear()
            _reranker_cache = None
