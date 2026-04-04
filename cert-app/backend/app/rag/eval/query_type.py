"""질의 유형 분류: 추천형 진단/평가용.

현재 운영에서는 query_type을 단순화해
`keyword` / `natural` / `mixed` 세 가지만 사용한다.

- keyword: "전공관련직무"처럼 **명사·키워드 위주 한 덩어리**로 끝나는 질의
- natural: "데이터 분석 쪽으로 가고싶어"처럼 **동사/희망 표현으로 끝나는 자연어 문장**
- mixed: "데이터 분석 쪽으로 가고싶어. 전공관련직무만"처럼 **자연어 문장 + 키워드 문장이 섞인 경우**

- keyword: 짧은 키워드 중심 질의, 도메인+취업형 ("IT 쪽 취업하고 싶어" 등)
- natural: 서술형/희망 표현이 있는 자연어 질의
- mixed: 둘 다 애매하거나 규칙으로 분류하기 어려운 경우
"""
import re
from typing import Optional

# 지원하는 query_type 값 (집계·표 일관용)
QUERY_TYPES = (
    "keyword",
    "natural",
    "mixed",
)


def classify_query_type(query: str, from_golden: Optional[str] = None) -> str:
    """
    query_type: keyword | natural | mixed

    - from_golden이 있고 세 가지 중 하나면 그대로 사용.
    - 없으면 규칙 기반으로 간단히 분류.
    """
    if from_golden and from_golden.strip() in QUERY_TYPES:
        return from_golden.strip()

    q = (query or "").strip()
    if not q:
        return "mixed"

    # 문장을 마침표/물음표/느낌표 기준으로 쪼개서
    # 각 조각을 "키워드형" vs "자연어형"으로 나눈 뒤 조합으로 최종 타입을 결정한다.
    clauses = [c.strip() for c in re.split(r"[.!?]", q) if c.strip()]
    if not clauses:
        return "mixed"

    def is_natural_clause(text: str) -> bool:
        """동사/희망 표현이 포함된 자연어 문장인지 판단."""
        # 대표적인 희망/동사 표현들
        if re.search(
            r"(가고\s*싶어|되고\s*싶어|일\s*하고\s*싶어|취업하고\s*싶어|하고\s*싶어|준비하려고|추천해줘|알고\s*싶어|궁금해|도움되는)",
            text,
        ):
            return True
        # "하고 싶어요/싶습니다" 존댓말 변형
        if re.search(r"(싶어요|싶습니다|하고\s*싶습니다)", text):
            return True
        # 문장 길이가 충분히 길고 종결 어미 느낌이 있으면 자연어로 본다.
        tokens = text.split()
        if len(tokens) >= 6 and re.search(r"(하다|되는|있다|있을까|일까|했으면)", text):
            return True
        return False

    def is_keyword_clause(text: str) -> bool:
        """'전공관련직무', '데이터 분석 직무'처럼 명사/키워드 위주의 짧은 덩어리인지 판단."""
        if is_natural_clause(text):
            return False
        tokens = text.split()
        # 너무 길면 키워드로 보지 않음
        if len(tokens) > 6:
            return False
        # 명사성 키워드에 자주 등장하는 토큰들
        keyword_hints = [
            "전공", "관련", "직무", "자격증", "추천", "로드맵", "위주", "중심",
            "쪽", "분야", "리스트", "정리", "만", "만!", "만요",
        ]
        # 동사/조동사 흔적이 거의 없고, 키워드 힌트가 섞여 있으면 키워드형으로 본다.
        if re.search(r"(가고\s*싶어|싶어|싶어요|싶습니다|하고\s*싶어)", text):
            return False
        if any(h in text for h in keyword_hints):
            return True
        # 공백이 거의 없고 한 단어로 끝나는 경우 (예: "전공관련직무")
        if len(tokens) == 1:
            return True
        return False

    has_natural = False
    has_keyword = False
    for c in clauses:
        if is_natural_clause(c):
            has_natural = True
        elif is_keyword_clause(c):
            has_keyword = True

    # 자연어 + 키워드 조합이면 mixed
    if has_natural and has_keyword:
        return "mixed"
    # 전부 자연어형이면 natural
    if has_natural and not has_keyword:
        return "natural"
    # 전부 키워드형이면 keyword
    if has_keyword and not has_natural:
        return "keyword"

    # 애매한 경우: 문장 하나인데 동사 표현이 있으면 natural, 아니면 keyword에 가깝게 본다.
    if len(clauses) == 1:
        return "natural" if is_natural_clause(clauses[0]) else "keyword"

    return "mixed"
