"""
OpenAI Embedding 유틸. MLOps: 레이턴시·토큰 로깅, Sentry 연동을 위한 예외 분류.
"""
import asyncio
import logging
import time
from typing import List

from openai import OpenAI, AsyncOpenAI

try:
    from openai import APIError, APIConnectionError, RateLimitError
except ImportError:
    APIError = APIConnectionError = RateLimitError = Exception  # type: ignore

from app.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

client = OpenAI(api_key=settings.OPENAI_API_KEY)
async_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)


def _log_embedding_usage(model: str, latency_ms: float, usage: object | None) -> None:
    """MLOps: 임베딩 호출 메트릭 로깅 (Sentry/모니터링 연동 가능)."""
    try:
        tokens = 0
        if usage is not None and hasattr(usage, "total_tokens"):
            tokens = getattr(usage, "total_tokens", 0) or 0
        logger.info(
            "embedding_inference model=%s latency_ms=%.0f input_tokens=%s",
            model, latency_ms, tokens,
            extra={"model_id": model, "latency_ms": latency_ms, "input_tokens": tokens},
        )
    except Exception as e:
        logger.debug("embedding usage log failed: %s", e)


def get_embedding(
    text: str,
    model: str = "text-embedding-3-small",
    retries: int = 3,
) -> List[float]:
    """Get embedding for text using OpenAI (sync, with retry)."""
    if not settings.OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY is not set.")
    text = text.replace("\n", " ").strip() or " "
    last_err: Exception | None = None
    for attempt in range(retries):
        try:
            start = time.perf_counter()
            response = client.embeddings.create(input=[text], model=model)
            if not getattr(response, "data", None):
                raise ValueError("OpenAI embedding returned no data")
            latency_ms = (time.perf_counter() - start) * 1000
            _log_embedding_usage(model, latency_ms, getattr(response, "usage", None))
            return response.data[0].embedding
        except (APIError, APIConnectionError, RateLimitError) as e:
            last_err = e
            logger.warning("OpenAI embedding attempt %s/%s failed: %s", attempt + 1, retries, type(e).__name__)
            if attempt == retries - 1:
                raise
            time.sleep(2**attempt)
        except Exception as e:
            last_err = e
            logger.exception("OpenAI embedding unexpected error")
            if attempt == retries - 1:
                raise
            time.sleep(2**attempt)
    raise RuntimeError("get_embedding unreachable") from last_err


async def get_embedding_async(
    text: str,
    model: str = "text-embedding-3-small",
    retries: int = 3,
) -> List[float]:
    """Get embedding for text using OpenAI (async, with retry)."""
    if not settings.OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY is not set.")
    text = text.replace("\n", " ").strip() or " "
    last_err: Exception | None = None
    for attempt in range(retries):
        try:
            start = time.perf_counter()
            response = await async_client.embeddings.create(input=[text], model=model)
            if not getattr(response, "data", None):
                raise ValueError("OpenAI embedding returned no data")
            latency_ms = (time.perf_counter() - start) * 1000
            _log_embedding_usage(model, latency_ms, getattr(response, "usage", None))
            return response.data[0].embedding
        except (APIError, APIConnectionError, RateLimitError) as e:
            last_err = e
            logger.warning("OpenAI embedding async attempt %s/%s failed: %s", attempt + 1, retries, type(e).__name__)
            if attempt == retries - 1:
                raise
            await _backoff_async(2**attempt)
        except Exception as e:
            last_err = e
            logger.exception("OpenAI embedding async unexpected error")
            if attempt == retries - 1:
                raise
            await _backoff_async(2**attempt)
    raise RuntimeError("get_embedding_async unreachable") from last_err


async def _backoff_async(seconds: float) -> None:
    """Non-blocking sleep for async retry backoff."""
    await asyncio.sleep(seconds)
