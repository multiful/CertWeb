import asyncio
import time
from openai import OpenAI, AsyncOpenAI
from app.config import get_settings
from typing import List

settings = get_settings()
client = OpenAI(api_key=settings.OPENAI_API_KEY)
async_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)


def get_embedding(
    text: str,
    model: str = "text-embedding-3-small",
    retries: int = 3,
) -> List[float]:
    """Get embedding for text using OpenAI (sync, with retry)."""
    if not settings.OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY is not set.")
    text = text.replace("\n", " ")
    for attempt in range(retries):
        try:
            return client.embeddings.create(input=[text], model=model).data[0].embedding
        except Exception as e:
            if attempt == retries - 1:
                raise
            time.sleep(2**attempt)
    raise RuntimeError("get_embedding unreachable")


async def get_embedding_async(
    text: str,
    model: str = "text-embedding-3-small",
    retries: int = 3,
) -> List[float]:
    """Get embedding for text using OpenAI (async, with retry)."""
    if not settings.OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY is not set.")
    text = text.replace("\n", " ")
    for attempt in range(retries):
        try:
            response = await async_client.embeddings.create(input=[text], model=model)
            return response.data[0].embedding
        except Exception as e:
            if attempt == retries - 1:
                raise
            await __backoff_async(2**attempt)
    raise RuntimeError("get_embedding_async unreachable")


async def __backoff_async(seconds: float) -> None:
    """Non-blocking sleep for async retry backoff."""
    await asyncio.sleep(seconds)
