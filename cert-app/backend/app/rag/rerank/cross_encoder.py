"""
경량 Cross-Encoder Reranker (로컬 모델 또는 원격 API).

- 로컬: sentence_transformers CrossEncoder 로드 (CPU 가능). RAG_CROSS_ENCODER_MODEL에 경로/모델명.
- 원격 API: RAG_CROSS_ENCODER_MODEL이 http(s):// 로 시작하면 해당 URL로 POST 요청 (HF Space 등).
  ONNX/경량화는 리랭커가 돌아가는 쪽(예: HF Space 앱)에서 적용. 본 코드는 POST로 query+passages 전달만 함.

API 규약 (원격 모드):
  POST {url}
  Body: {"query": str, "passages": [str, ...]}
  Response: {"scores": [float, ...]}  (passages와 동일 순서)

캐싱:
  - (query, doc_hash) 쌍에 대해 score를 in-memory LRU 캐시에 저장
  - cache hit 시 API 호출 없이 score 재사용
  - cache miss만 모아서 batch API 호출
"""
import logging
import time
from typing import Dict, List, Optional, Tuple

from app.rag.rerank.cache import RerankerCache, get_reranker_cache

logger = logging.getLogger(__name__)
_reranker = None


def _is_reranker_api_url(value: str) -> bool:
    return value.strip().startswith("http://") or value.strip().startswith("https://")


def _rerank_via_api(
    api_url: str,
    query: str,
    pairs: List[Tuple[str, str]],
    top_k: Optional[int],
    use_cache: bool = True,
) -> List[Tuple[str, float]]:
    """
    원격 Reranker API 호출 (캐싱 적용).
    
    - cache hit: API 호출 없이 캐시된 score 사용
    - cache miss: batch API 호출 후 캐시에 저장
    - 실패 시 빈 리스트 반환
    """
    import httpx
    
    if not pairs:
        return []
    
    cache = get_reranker_cache() if use_cache else None
    
    # 1) 캐시에서 hit 조회
    cached_scores: Dict[str, float] = {}  # chunk_id -> score
    miss_pairs: List[Tuple[str, str, str]] = []  # (chunk_id, text, doc_hash)
    
    for chunk_id, text in pairs:
        doc_hash = RerankerCache.hash_document(text)
        if cache:
            score = cache.get(query, doc_hash)
            if score is not None:
                cached_scores[chunk_id] = score
                continue
        miss_pairs.append((chunk_id, text, doc_hash))
    
    # 2) miss 항목만 API 호출
    api_scores: Dict[str, float] = {}  # chunk_id -> score
    if miss_pairs:
        passages = [text for _cid, text, _dh in miss_pairs]
        try:
            start = time.perf_counter()
            with httpx.Client(timeout=90.0) as client:
                r = client.post(
                    api_url.rstrip("/"),
                    json={"query": query, "passages": passages},
                    headers={"Content-Type": "application/json"},
                )
                r.raise_for_status()
                data = r.json()
                scores = data.get("scores")
                latency_ms = (time.perf_counter() - start) * 1000
                
                if not isinstance(scores, list) or len(scores) != len(miss_pairs):
                    logger.warning(
                        "리랭커 API 응답 형식 오류: scores 길이=%s, pairs=%d",
                        len(scores) if scores else 0, len(miss_pairs)
                    )
                    # fallback: 캐시된 것만 반환
                    if cached_scores:
                        out = [(cid, s) for cid, s in cached_scores.items()]
                        out.sort(key=lambda x: -x[1])
                        return out[:top_k] if top_k else out
                    return []
                
                # 캐시에 저장
                for i, (chunk_id, text, doc_hash) in enumerate(miss_pairs):
                    score = float(scores[i])
                    api_scores[chunk_id] = score
                    if cache:
                        cache.set(query, doc_hash, score)
                
                logger.debug(
                    "Reranker API: %d hit, %d miss, latency=%.1fms",
                    len(cached_scores), len(miss_pairs), latency_ms
                )
                
        except Exception as e:
            logger.exception(
                "리랭커 API 호출 실패 (url=%s, query 길이=%d, miss=%d): %s",
                api_url, len(query), len(miss_pairs), e
            )
            # fallback: 캐시된 것만 반환
            if cached_scores:
                out = [(cid, s) for cid, s in cached_scores.items()]
                out.sort(key=lambda x: -x[1])
                return out[:top_k] if top_k else out
            return []
    
    # 3) 결과 병합 및 정렬
    all_scores = {**cached_scores, **api_scores}
    out = [(cid, s) for cid, s in all_scores.items()]
    out.sort(key=lambda x: -x[1])
    
    if top_k is not None:
        out = out[:top_k]
    
    return out


def _get_reranker(model_name: str):
    """싱글톤 CrossEncoder. 로드 실패 시 None (원인은 로그에 기록)."""
    global _reranker
    if _reranker is not None:
        return _reranker
    try:
        from sentence_transformers import CrossEncoder
        _reranker = CrossEncoder(model_name)
        return _reranker
    except Exception as e:
        logger.exception(
            "리랭커 모델 로드 실패 (model=%s). OOM이면 배치 축소/GPU 사용, 호환 문제면 RAG_CROSS_ENCODER_MODEL 확인: %s",
            model_name,
            e,
        )
        return None


def rerank_with_cross_encoder(
    query: str,
    pairs: List[Tuple[str, str]],
    model_name: Optional[str] = None,
    top_k: Optional[int] = None,
    use_cache: Optional[bool] = None,
) -> List[Tuple[str, float]]:
    """
    (chunk_id, text) 쌍에 대해 query와의 관련도 점수 계산 후 점수 순 정렬.
    pairs: [(chunk_id, text), ...]
    반환: [(chunk_id, score), ...] (점수 내림차순). 실패 시 빈 리스트.

    RAG_CROSS_ENCODER_MODEL이 http(s):// 이면 로컬 모델 없이 해당 URL로 API 호출.
    캐싱: use_cache=True이면 (query, doc_hash) pair 캐싱 적용 (기본: 설정에 따름).
    """
    if not query or not pairs:
        return []
    from app.rag.config import get_rag_settings
    settings = get_rag_settings()
    name = (model_name or settings.RAG_CROSS_ENCODER_MODEL).strip()
    
    # 캐시 사용 여부 결정
    if use_cache is None:
        use_cache = getattr(settings, "RAG_RERANK_CACHE_ENABLE", True)
    
    if _is_reranker_api_url(name):
        return _rerank_via_api(name, query, pairs, top_k, use_cache=use_cache)
    
    # 로컬 모델은 캐싱 없이 직접 호출 (로컬이라 빠름)
    model = _get_reranker(name)
    if model is None:
        return []
    try:
        to_score = [(query, text) for _cid, text in pairs]
        scores = model.predict(to_score)
        if hasattr(scores, "tolist"):
            scores = scores.tolist()
        out = [(pairs[i][0], float(scores[i])) for i in range(len(pairs))]
        out.sort(key=lambda x: -x[1])
        if top_k is not None:
            out = out[:top_k]
        return out
    except Exception as e:
        logger.exception("리랭커 predict 실패 (query 길이=%d, pairs=%d): %s", len(query), len(pairs), e)
        return []


def get_reranker_cache_stats() -> Dict:
    """캐시 통계 반환 (진단용)."""
    cache = get_reranker_cache()
    return cache.stats()
