"""
OpenAI Embedding 유틸. MLOps: 레이턴시·토큰 로깅, Sentry 연동을 위한 예외 분류.
"""
import asyncio
import json
import logging
import time
from typing import List, Optional

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


async def expand_query_async(
    major: str,
    interest: Optional[str],
    model: str = "gpt-4o-mini",
) -> str:
    """
    HyDE-style Query Expansion: 전공+관심사를 임베딩 전에 풍부한 키워드 집합으로 확장.
    임베딩 쿼리 품질을 높여 시멘틱 검색 정확도를 향상시킨다.
    실패 시 원본 쿼리 반환 (safe fallback, 서비스 중단 없음).
    """
    if not settings.OPENAI_API_KEY:
        return f"{major} {interest or ''}".strip()

    prompt_parts = [f"전공: {major}"]
    if interest:
        prompt_parts.append(f"커리어 목표: {interest}")

    try:
        start = time.perf_counter()
        response = await async_client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "당신은 자격증 및 직무 전문가입니다. "
                        "주어진 전공과 커리어 목표에 관련된 핵심 기술, 직무, 산업 분야, "
                        "자격증 유형을 한국어로 나열합니다. "
                        "답변은 콤마로 구분된 키워드 목록 형식으로만 작성하세요. 설명 없이."
                    ),
                },
                {
                    "role": "user",
                    "content": "\n".join(prompt_parts)
                    + "\n\n관련 키워드를 20개 이내로 나열하세요.",
                },
            ],
            max_tokens=180,
            temperature=0.2,
        )
        latency_ms = (time.perf_counter() - start) * 1000
        logger.info("expand_query latency_ms=%.0f major=%s", latency_ms, major)
        expanded = (response.choices[0].message.content or "").strip()
        # 원본 + 확장 키워드 결합 → 임베딩 품질 극대화
        base = f"{major} {interest or ''}".strip()
        return f"{base} {expanded}"[:900]
    except Exception as e:
        logger.warning("expand_query_async failed (safe fallback): %s", e)
        return f"{major} {interest or ''}".strip()


async def llm_rerank_and_reason(
    major: str,
    interest: Optional[str],
    candidates: List[dict],
    top_n: int = 10,
    grade_year: Optional[int] = None,
    skill_level: Optional[float] = None,
) -> List[dict]:
    """
    Cross-encoder 방식 Re-ranking + 이유 생성 (단일 GPT-4o-mini 호출).

    RRF로 1차 정렬된 후보 (최대 20개)를 GPT에게 넘겨,
    사용자 맥락에 따라 최적 top_n개를 선정·재정렬하고 맞춤형 이유를 동시에 생성한다.

    Returns: [{"qual_id": int, "reason": str}, ...] (LLM이 선택한 순서)
    실패 시 빈 리스트 반환 → 호출자가 기존 RRF 순서 + generate_reasons_batch로 폴백.
    """
    if not candidates or not settings.OPENAI_API_KEY:
        return []

    context_parts = [f"전공: {major}"]
    if interest:
        context_parts.append(f"커리어 목표/관심사: {interest}")
    if grade_year is not None:
        context_parts.append(f"현재 {grade_year}학년")
    if skill_level is not None:
        context_parts.append(f"기존 자격증 평균 난이도: {skill_level:.1f}/10")
    context = " | ".join(context_parts)

    cert_lines = []
    for i, c in enumerate(candidates, 1):
        pr = f" (합격률 {c['pass_rate']:.0f}%)" if c.get("pass_rate") is not None else ""
        cert_lines.append(f"{i}. [id:{c['qual_id']}] {c['qual_name']}{pr}")

    total = len(candidates)
    pick = min(top_n, total)

    prompt = (
        f"사용자 프로필: {context}\n\n"
        f"다음 {total}개 자격증 후보 중 이 사용자에게 가장 적합한 {pick}개를 선택하고 "
        f"최적 순서로 정렬한 뒤, 각각에 대한 추천 이유를 1~2문장으로 작성하세요.\n\n"
        "후보 목록:\n" + "\n".join(cert_lines) +
        f"\n\n규칙:\n"
        f"- 정확히 {pick}개 선택 (중복 없이)\n"
        "- qual_id는 목록에 있는 숫자만 사용 (절대 추가/변조 금지)\n"
        "- 가장 적합한 순서로 나열 (1번이 최우선)\n"
        "- 이유는 구체적이고 사용자 프로필과 연계하여 작성\n"
        f'JSON: {{"ranked": [{{"qual_id": 숫자, "reason": "추천 이유"}}, ...]}}'
    )

    try:
        start = time.perf_counter()
        response = await async_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "당신은 전문 자격증 커리어 컨설턴트입니다. "
                        "주어진 후보 목록에서 사용자 프로필에 최적인 자격증을 선별·재정렬하고 "
                        "각 자격증에 대한 맞춤형 추천 이유를 한국어로 작성합니다. "
                        "반드시 JSON만 반환하세요."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            max_tokens=900,
            temperature=0.5,
            response_format={"type": "json_object"},
        )
        latency_ms = (time.perf_counter() - start) * 1000
        usage = getattr(response, "usage", None)
        tokens = getattr(usage, "total_tokens", 0) if usage else 0
        logger.info(
            "llm_rerank latency_ms=%.0f total_tokens=%s candidates=%s top_n=%s",
            latency_ms, tokens, total, pick,
        )
        content = response.choices[0].message.content or "{}"
        data = json.loads(content)
        ranked: List[dict] = data.get("ranked", [])

        # 환각 방지: 원본 qual_id 집합에 없는 항목 제거
        valid_ids = {c["qual_id"] for c in candidates}
        sanitized = [r for r in ranked if isinstance(r.get("qual_id"), int) and r["qual_id"] in valid_ids]
        # 중복 제거 (LLM이 같은 id를 두 번 반환할 경우 대비)
        seen: set[int] = set()
        deduped = []
        for r in sanitized:
            if r["qual_id"] not in seen:
                seen.add(r["qual_id"])
                deduped.append(r)

        if len(deduped) >= pick:
            return deduped[:pick]

        logger.warning(
            "llm_rerank_and_reason: returned %d valid items, expected %d — falling back",
            len(deduped), pick,
        )
        return []
    except Exception as e:
        logger.warning("llm_rerank_and_reason failed (non-fatal): %s", e)
        return []


async def generate_reasons_batch(
    major: str,
    interest: Optional[str],
    candidates: List[dict],
    grade_year: Optional[int] = None,
    skill_level: Optional[float] = None,
) -> List[str]:
    """
    GPT-4o-mini로 추천 자격증에 대한 맞춤형 이유를 일괄 생성.
    candidates: [{"qual_name": ..., "pass_rate": ...}, ...]
    반환: reasons 문자열 리스트 (candidates 순서와 동일)
    실패 시 빈 리스트 반환 (호출자가 fallback 처리).
    """
    if not candidates or not settings.OPENAI_API_KEY:
        return []

    context_parts = [f"전공: {major}"]
    if interest:
        context_parts.append(f"커리어 목표: {interest}")
    if grade_year is not None:
        context_parts.append(f"현재 {grade_year}학년")
    if skill_level is not None:
        context_parts.append(f"기존 자격증 평균 난이도: {skill_level:.1f}/10")
    context = " | ".join(context_parts)

    cert_lines = []
    for i, c in enumerate(candidates, 1):
        pr = f" (합격률 {c['pass_rate']:.1f}%)" if c.get("pass_rate") is not None else ""
        cert_lines.append(f"{i}. {c['qual_name']}{pr}")

    prompt = (
        f"사용자 프로필: {context}\n\n"
        f"추천 자격증 목록:\n" + "\n".join(cert_lines) +
        "\n\n각 자격증이 이 사용자에게 왜 적합한지 1~2문장으로 한국어 설명을 작성하세요. "
        "구체적이고 실용적인 이유를 포함하세요. "
        'JSON 형식으로만 반환: {"reasons": ["이유1", "이유2", ...]}'
    )

    try:
        start = time.perf_counter()
        response = await async_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "당신은 전문 자격증 커리어 컨설턴트입니다. "
                        "주어진 사용자 프로필에 맞게 각 자격증의 추천 이유를 간결하고 실용적으로 설명합니다."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            max_tokens=700,
            temperature=0.65,
            response_format={"type": "json_object"},
        )
        latency_ms = (time.perf_counter() - start) * 1000
        usage = getattr(response, "usage", None)
        tokens = getattr(usage, "total_tokens", 0) if usage else 0
        logger.info(
            "llm_reason_gen latency_ms=%.0f total_tokens=%s candidates=%s",
            latency_ms, tokens, len(candidates),
        )
        content = response.choices[0].message.content or "{}"
        data = json.loads(content)
        reasons: List[str] = data.get("reasons", [])
        if len(reasons) == len(candidates):
            return reasons
        logger.warning("generate_reasons_batch: reason count mismatch %d vs %d", len(reasons), len(candidates))
        return []
    except Exception as e:
        logger.warning("generate_reasons_batch failed (non-fatal): %s", e)
        return []
