"""
Reranker: HF Space API 전용 (로컬 Cross-Encoder 미사용).

- RAG_RERANKER_API_URL에 HF Space inference URL 설정 시 해당 URL로 POST (query, passages) → scores.
- 모델: multifuly/certweb-reranker-model, Space: multifuly/certweb-reranker.

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

from app.rag.config import get_rag_settings
from app.rag.rerank.cache import RerankerCache, get_reranker_cache

logger = logging.getLogger(__name__)


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
    
    if cache and cached_scores:
        logger.info(
            "Reranker cache: %d hits, %d miss (캐시 적용됨)",
            len(cached_scores), len(miss_pairs)
        )
    
    # 2) miss 항목만 API 호출 (5xx/429/연결 오류 시 RAG_RERANKER_HTTP_RETRIES 만큼 지수 백오프 재시도)
    api_scores: Dict[str, float] = {}  # chunk_id -> score
    if miss_pairs:
        passages = [text for _cid, text, _dh in miss_pairs]
        settings = get_rag_settings()
        timeout = float(getattr(settings, "RAG_RERANKER_TIMEOUT", 90.0) or 90.0)
        max_retries = int(getattr(settings, "RAG_RERANKER_HTTP_RETRIES", 2) or 2)
        api_ok = False
        for attempt in range(max_retries + 1):
            try:
                start = time.perf_counter()
                with httpx.Client(timeout=timeout) as client:
                    r = client.post(
                        api_url.rstrip("/"),
                        json={"query": query, "passages": passages},
                        headers={"Content-Type": "application/json"},
                    )
                    if r.status_code >= 500 or r.status_code == 429:
                        if attempt < max_retries:
                            delay = min(3.0, 0.5 * (2**attempt))
                            logger.warning(
                                "리랭커 API HTTP %s (시도 %d/%d), %.1fs 후 재시도",
                                r.status_code,
                                attempt + 1,
                                max_retries + 1,
                                delay,
                            )
                            time.sleep(delay)
                            continue
                    r.raise_for_status()
                    data = r.json()
                    scores = data.get("scores")
                    latency_ms = (time.perf_counter() - start) * 1000

                    if not isinstance(scores, list) or len(scores) != len(miss_pairs):
                        logger.warning(
                            "리랭커 API 응답 형식 오류: scores 길이=%s, pairs=%d",
                            len(scores) if scores else 0,
                            len(miss_pairs),
                        )
                        if cached_scores:
                            out = [(cid, s) for cid, s in cached_scores.items()]
                            out.sort(key=lambda x: -x[1])
                            return out[:top_k] if top_k else out
                        return []

                    for i, (chunk_id, text, doc_hash) in enumerate(miss_pairs):
                        score = float(scores[i])
                        api_scores[chunk_id] = score
                        if cache:
                            cache.set(query, doc_hash, score)

                    logger.debug(
                        "Reranker API: %d hit, %d miss, latency=%.1fms",
                        len(cached_scores),
                        len(miss_pairs),
                        latency_ms,
                    )
                    api_ok = True
                    break
            except httpx.HTTPStatusError as e:
                code = e.response.status_code if e.response is not None else 0
                if (code >= 500 or code == 429) and attempt < max_retries:
                    delay = min(3.0, 0.5 * (2**attempt))
                    logger.warning(
                        "리랭커 API HTTP %s, %.1fs 후 재시도",
                        code,
                        delay,
                    )
                    time.sleep(delay)
                    continue
                logger.warning(
                    "리랭커 API HTTP 오류 (url=%s, status=%s): %s",
                    api_url,
                    code,
                    e,
                )
                break
            except httpx.RequestError as e:
                if attempt < max_retries:
                    delay = min(3.0, 0.5 * (2**attempt))
                    logger.warning(
                        "리랭커 API 연결 실패 (시도 %d/%d), %.1fs 후 재시도: %s",
                        attempt + 1,
                        max_retries + 1,
                        delay,
                        e,
                    )
                    time.sleep(delay)
                    continue
                logger.warning(
                    "리랭커 API 연결 실패 (url=%s, query 길이=%d, miss=%d): %s",
                    api_url,
                    len(query),
                    len(miss_pairs),
                    e,
                )
                break
            except Exception as e:
                logger.exception(
                    "리랭커 API 호출 실패 (url=%s, query 길이=%d, miss=%d): %s",
                    api_url,
                    len(query),
                    len(miss_pairs),
                    e,
                )
                break
        if not api_ok:
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

    RAG_RERANKER_API_URL 또는 model_name이 http(s) URL이면 해당 URL로 API 호출 (HF Space).
    캐싱: use_cache=True이면 (query, doc_hash) pair 캐싱 적용 (기본: 설정에 따름).
    """
    if not query or not pairs:
        return []
    from app.rag.config import get_rag_settings
    settings = get_rag_settings()
    url = (model_name or getattr(settings, "RAG_RERANKER_API_URL", "") or "").strip()
    
    if not url:
        logger.warning("RAG_RERANKER_API_URL 미설정 — 리랭커 스킵 (원격 HF Space 사용 시 .env 또는 환경변수 설정 필요)")
        return []
    
    if use_cache is None:
        use_cache = getattr(settings, "RAG_RERANK_CACHE_ENABLE", True)
    
    if _is_reranker_api_url(url):
        return _rerank_via_api(url, query, pairs, top_k, use_cache=use_cache)
    
    logger.warning("RAG_RERANKER_API_URL이 URL 형식이 아님 — 리랭커 스킵 (로컬 모델 미지원)")
    return []


def get_reranker_cache_stats() -> Dict:
    """캐시 통계 반환 (진단용)."""
    cache = get_reranker_cache()
    return cache.stats()
