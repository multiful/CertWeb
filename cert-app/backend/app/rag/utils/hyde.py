"""
HyDE (Hypothetical Document Embeddings): 질의에 대한 가상 답변 문서를 생성해 벡터 검색에 활용.
논문: Gao et al., "Precise Zero-Shot Dense Retrieval without Relevance Labels", 2022.
다양한 표현으로 검색해 recall·nDCG 향상. RRF로 기존 BM25·Vector와 3-way 병합.
"""
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# 프롬프트: 자격증/취업 문맥의 가상 문서 1~2문장 생성 (검색용이므로 키워드·직무·자격증명 포함 유도)
HYDE_SYSTEM = (
    "당신은 자격증·취업 로드맵 안내 전문가입니다. "
    "주어진 질문에 대해, 관련 자격증 설명문이나 취업 가이드 문단처럼 읽히는 짧은 문장 1~2개를 작성하세요. "
    "자격증명(정보처리기사, SQLD, ADsP 등), 직무(개발, 데이터 분석 등), 키워드는 실제로 있을 법한 표현으로 포함하세요. "
    "질문을 그대로 반복하지 말고, 답변 문서처럼 서술하세요."
)
HYDE_USER_TEMPLATE = "질문: {query}\n\n위 질문에 답하는 것처럼, 자격증·취업 관련 설명 문단 1~2문장을 작성하세요 (검색용 가상 문서):"


def generate_hyde_document(query: str, max_tokens: int = 150) -> Optional[str]:
    """
    질의에 대한 가상 답변 문서(1~2문장)를 LLM으로 생성.
    실패 시 None 반환. 호출부에서 HyDE 채널 생략 또는 fallback.
    """
    if not (query or "").strip():
        return None
    try:
        from app.config import get_settings
        from app.rag.config import get_rag_settings
        from openai import OpenAI
        settings = get_settings()
        if not getattr(settings, "OPENAI_API_KEY", None):
            return None
        rag = get_rag_settings()
        temperature = getattr(rag, "RAG_HYDE_TEMPERATURE", 0.3)
        client = OpenAI(api_key=settings.OPENAI_API_KEY)
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": HYDE_SYSTEM},
                {"role": "user", "content": HYDE_USER_TEMPLATE.format(query=query.strip())},
            ],
            max_tokens=max_tokens,
            temperature=temperature,
        )
        text = (resp.choices[0].message.content or "").strip()
        if not text or len(text) < 10:
            return None
        return text[:800]  # 과도한 길이 방지
    except Exception as e:
        logger.warning("HyDE document generation failed: %s", e)
        return None
