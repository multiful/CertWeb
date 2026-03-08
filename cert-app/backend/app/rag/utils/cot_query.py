"""
COT(Chain-of-Thought) 기반 쿼리 확장·메타 쿼리.
- COT 확장: 질의 의도를 단계적으로 추론한 뒤, 검색에 쓸 대안 질의 2~3개 생성 → 다중 벡터 검색 RRF.
- Step-back: 질의 뒤에 있는 "상위 목표(역할·커리어)"를 한 문장으로 추출 → 메타 쿼리로 추가 검색.
"""
import logging
import re
from typing import List, Optional

logger = logging.getLogger(__name__)

# COT: 단계적 추론 후 대안 검색어 생성 (한 줄당 하나, 번호/불릿 제거해 파싱)
COT_SYSTEM = (
    "당신은 자격증·취업 검색 전문가입니다. 사용자 질문의 의도를 단계적으로 생각한 뒤, "
    "같은 의도를 다른 표현으로 검색할 때 쓸 수 있는 **대안 검색 문구 2~3개**만 출력하세요. "
    "각 문구는 한 줄에 하나. 자격증명(정보처리기사, SQLD 등), 직무(개발, 데이터 등), 목적(취업, 이직 등) 키워드를 포함할 수 있습니다. "
    "설명이나 번호 없이 검색 문구만 한 줄에 하나씩 출력하세요."
)
COT_USER_TEMPLATE = "질문: {query}\n\n위 질문과 같은 의도로 검색할 때 쓸 수 있는 대안 문구 2~3개 (한 줄에 하나):"

# Step-back: 질의에서 상위 목표(역할·커리어·학습 목표) 한 문장 추출
STEPBACK_SYSTEM = (
    "당신은 사용자 질문을 해석하는 보조입니다. "
    "질문 뒤에 숨은 **상위 목표**(희망 직무, 커리어 단계, 배우고 싶은 분야 등)를 한 문장으로 요약하세요. "
    "검색어로 쓸 수 있게 짧게 (10단어 이내). 예: '데이터 분석 직무 취업', '정보처리 자격증 로드맵'."
)
STEPBACK_USER_TEMPLATE = "질문: {query}\n\n이 질문에서 사용자가 궁극적으로 원하는 목표를 한 문장 검색어로:"


def expand_query_cot(query: str, max_alternatives: int = 2) -> List[str]:
    """
    COT로 질의 의도 추론 후 대안 검색 문구 2~3개 생성.
    반환: 대안 문구 리스트(최대 max_alternatives개). 실패 시 빈 리스트.
    """
    if not (query or "").strip():
        return []
    try:
        from app.config import get_settings
        from openai import OpenAI
        settings = get_settings()
        if not getattr(settings, "OPENAI_API_KEY", None):
            return []
        client = OpenAI(api_key=settings.OPENAI_API_KEY)
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": COT_SYSTEM},
                {"role": "user", "content": COT_USER_TEMPLATE.format(query=query.strip())},
            ],
            max_tokens=150,
            temperature=0.3,
        )
        text = (resp.choices[0].message.content or "").strip()
        if not text:
            return []
        # 한 줄당 하나, 번호·불릿 제거
        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
        out: List[str] = []
        for ln in lines[: max_alternatives + 2]:
            ln = re.sub(r"^[\d\-*\.\)]\s*", "", ln).strip()
            if len(ln) >= 2 and ln not in out:
                out.append(ln[:200])
        return out[:max_alternatives]
    except Exception as e:
        logger.warning("COT query expansion failed: %s", e)
        return []


def stepback_query(query: str) -> Optional[str]:
    """
    질의에서 상위 목표(역할·커리어·학습 목표)를 한 문장 검색어로 추출.
    실패 시 None.
    """
    if not (query or "").strip():
        return None
    try:
        from app.config import get_settings
        from openai import OpenAI
        settings = get_settings()
        if not getattr(settings, "OPENAI_API_KEY", None):
            return None
        client = OpenAI(api_key=settings.OPENAI_API_KEY)
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": STEPBACK_SYSTEM},
                {"role": "user", "content": STEPBACK_USER_TEMPLATE.format(query=query.strip())},
            ],
            max_tokens=80,
            temperature=0.2,
        )
        text = (resp.choices[0].message.content or "").strip()
        if not text or len(text) < 2:
            return None
        return text[:150]
    except Exception as e:
        logger.warning("Step-back query failed: %s", e)
        return None
