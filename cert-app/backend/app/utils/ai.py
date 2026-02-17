from openai import OpenAI
from app.config import get_settings
from typing import List

settings = get_settings()
client = OpenAI(api_key=settings.OPENAI_API_KEY)

def get_embedding(text: str, model: str = "text-embedding-3-small") -> List[float]:
    """Get embedding for text using OpenAI."""
    if not settings.OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY is not set.")
    
    text = text.replace("\n", " ")
    return client.embeddings.create(input=[text], model=model).data[0].embedding
