"""
Answerability gating: retrieval confidence 낮으면 "근거 부족" + 추가질문 1~2개 반환.
"""
from dataclasses import dataclass
from typing import List, Optional, Tuple

from app.rag.config import get_rag_settings


@dataclass
class GatingResult:
    """gating 적용 시 반환 구조."""
    applied: bool  # True면 "근거 부족" 응답
    answer: str
    suggested_questions: List[str]


def check_gating(
    top1_score: float,
    chunks: List[Tuple[str, str, float]],
    query: str,
) -> GatingResult:
    """
    top1_score가 임계값 미만이거나 근거 개수가 부족하면 gating 적용.
    """
    settings = get_rag_settings()
    min_score = settings.RAG_GATING_TOP1_MIN_SCORE
    min_evidence = settings.RAG_GATING_MIN_EVIDENCE_COUNT

    if top1_score >= min_score and len(chunks) >= min_evidence:
        return GatingResult(
            applied=False,
            answer="",
            suggested_questions=[],
        )

    suggested = [
        "어떤 분야(전공/직무)의 자격증을 찾고 계신가요?",
        "필기/실기 중 어떤 시험 정보가 필요하신가요?",
    ]
    answer = (
        "제공된 근거가 부족하여 신뢰할 수 있는 답변을 드리기 어렵습니다. "
        "아래 질문을 참고해 더 구체적으로 질문해 주시면 도움이 됩니다."
    )
    return GatingResult(
        applied=True,
        answer=answer,
        suggested_questions=suggested[:2],
    )
