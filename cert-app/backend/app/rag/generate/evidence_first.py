"""
Evidence-first 생성: 근거 bullet 3~6개 → 최종 답변, 문장 끝 [chunk_id] citation 강제.
OpenAI API 사용 (기존 app.config OPENAI_API_KEY). 없으면 템플릿 폴백.
"""
import logging
import re
from typing import List, Optional, Tuple

from app.config import get_settings
from app.rag.config import get_rag_settings

logger = logging.getLogger(__name__)


def generate_evidence_first_answer(
    query: str,
    chunks: List[Tuple[str, str, float]],
    max_evidence: int = 6,
) -> Tuple[str, List[str], List[str]]:
    """
    chunks: [(chunk_id, content, score), ...]
    반환: (answer, evidence_bullets, citation_chunk_ids)
    """
    settings = get_settings()
    rag_settings = get_rag_settings()
    n = min(max_evidence, max(3, len(chunks)))
    selected = chunks[:n]
    if not selected:
        return "관련 근거를 찾지 못했습니다.", [], []

    evidence_bullets = []
    citation_ids = []
    for cid, content, _ in selected:
        content_preview = (content or "").strip()[:500]
        evidence_bullets.append(f"[{cid}] {content_preview}")
        citation_ids.append(cid)

    if not settings.OPENAI_API_KEY:
        # 폴백: 근거 나열 + "위 근거를 바탕으로 답변합니다."
        answer = "다음 근거를 바탕으로 답변합니다.\n\n"
        answer += "\n\n".join(evidence_bullets)
        answer += "\n\n(자세한 답변은 OPENAI_API_KEY 설정 후 이용 가능합니다.)"
        return answer, evidence_bullets, citation_ids

    try:
        from openai import OpenAI
        client = OpenAI(api_key=settings.OPENAI_API_KEY)
        context = "\n\n".join(evidence_bullets)
        system_msg = (
            "당신은 자격증 정보 안내 봇입니다. 아래 근거만 사용해 답하세요. "
            "근거에 없는 내용은 말하지 마세요. 답변 문장 끝에 해당 근거의 [chunk_id]를 반드시 표기하세요."
        )
        prompt = f"""다음은 자격증 관련 검색 근거입니다. 질문에 대해 이 근거만 사용해 답변하세요.
답변의 핵심 문장 끝에 반드시 해당 근거의 [chunk_id]를 표시하세요. 예: ...입니다.[123:0]

근거:
{context}

질문: {query}

답변 (근거만 사용, 문장 끝에 [chunk_id] 표기):"""
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": prompt},
            ],
            max_tokens=800,
            temperature=0.2,
        )
        answer = (resp.choices[0].message.content or "").strip()
        if not answer:
            answer = "근거를 바탕으로 답변을 생성하지 못했습니다."
        # Citation 보강: 답변에 [chunk_id] 패턴이 없으면 참고 줄 추가
        if not re.search(r"\[\d+:\d+\]", answer):
            answer += "\n\n참고: " + ", ".join(f"[{c[0]}]" for c in selected)
        return answer, evidence_bullets, citation_ids
    except Exception as e:
        logger.warning("evidence_first LLM failed: %s", e)
        answer = "다음 근거를 바탕으로 답변합니다.\n\n" + "\n\n".join(evidence_bullets)
        return answer, evidence_bullets, citation_ids
