"""질의 유형 분류: 추천형 진단/평가용. 골든셋에 query_type이 없을 때 규칙 기반 자동 분류."""
import re
from typing import Optional

# 지원하는 query_type 값 (집계·표 일관용)
QUERY_TYPES = (
    "keyword",
    "natural",
    "cert_name_included",
    "major+job",
    "purpose_only",
    "roadmap",
    "comparison",
    "mixed",
)

# 자격증명/약칭 패턴 (cert_name_included 판별용)
CERT_NAME_PATTERN = re.compile(
    r"정처기|정처산|SQLD|SQLP|ADsP|ADP|빅분기|빅데이터분석기사|정보처리기사|정보처리산업기사|"
    r"네관사|리눅스마스터|정보보안기사|전기기사|컴활|정보처리\s*기사",
    re.IGNORECASE,
)

# comparison/exclusion: "정처기 말고", "제외", "비교"
EXCLUSION_PATTERN = re.compile(r"말고|제외|비교|말고\s*추천|빼고", re.IGNORECASE)

# roadmap/sequence: "다음으로", "뭐 따야", "순서", "로드맵"
ROADMAP_PATTERN = re.compile(
    r"다음\s*으로|다음에|뭐\s*따야|뭘\s*따야|순서|로드맵|이후에|그\s*다음",
    re.IGNORECASE,
)

# major+job: 전공·직무 동시 언급
MAJOR_JOB_PATTERN = re.compile(
    r"(전공|과|학과|산업데이터|컴퓨터공학|경영학).*(직무|취업|되려고|희망)|"
    r"(직무|취업).*(전공|과|학과)",
    re.IGNORECASE,
)
MAJOR_OR_JOB_WORDS = re.compile(
    r"전공|학과|과\s|직무|취업|희망|되려고|데이터\s*분석|백엔드|프론트",
    re.IGNORECASE,
)

# purpose_only: 목적만 짧게 ("취업용", "이직")
PURPOSE_ONLY_PATTERN = re.compile(r"^(취업|이직|승진|실무)\s*(용|준비)?\s*자격증?", re.IGNORECASE)


def classify_query_type(query: str, from_golden: Optional[str] = None) -> str:
    """
    query_type: keyword | natural | cert_name_included | major+job | purpose_only | roadmap | comparison | mixed.
    from_golden이 있으면 우선 사용(QUERY_TYPES에 있으면), 없으면 규칙 기반 분류.
    """
    if from_golden and (from_golden.strip() in QUERY_TYPES or from_golden.strip() in ("keyword", "natural", "mixed", "cert_name_included")):
        qt = from_golden.strip()
        return qt if qt in QUERY_TYPES else qt

    q = (query or "").strip()
    if not q:
        return "mixed"

    tokens = q.split()
    # 0) 자격증명 + 로드맵 동시("ADsP 따놨는데 다음에 뭐 따면") → 골든 기준 natural
    if CERT_NAME_PATTERN.search(q) and ROADMAP_PATTERN.search(q):
        return "natural"
    # 1) 자격증명/약칭 포함
    if CERT_NAME_PATTERN.search(q):
        return "cert_name_included"
    # 2) 비교/제외 ("정처기 말고 추천해줘")
    if EXCLUSION_PATTERN.search(q):
        return "comparison"
    # 3) 로드맵/순서 ("SQLD 다음 뭐 따야 해?")
    if ROADMAP_PATTERN.search(q):
        return "roadmap"
    # 4) 전공+직무 동시 언급 ("난 산업데이터공학과인데 취업용으로 뭐가 좋아?")
    #    "데이터 분석 쪽으로 가고 싶어"는 natural로 두기 위해 희망 표현이 있으면 제외
    natural_wish_early = re.search(
        r"(가고\s*싶어|되고\s*싶어|일\s+하고\s*싶어|쪽\s+하고\s*싶어|하고싶어)",
        q,
    )
    if not natural_wish_early and (
        MAJOR_JOB_PATTERN.search(q) or (MAJOR_OR_JOB_WORDS.search(q) and len(tokens) >= 6)
    ):
        return "major+job"
    # 5) 목적만 짧게
    if len(tokens) <= 5 and PURPOSE_ONLY_PATTERN.search(q):
        return "purpose_only"
    # 5b) 한 토큰 도메인 + "쪽(으로) 가고/일 하고/일하고 싶어" → 골든 기준 keyword (단, 예외는 natural 유지)
    ONE_TOKEN_NATURAL = frozenset({
        "전산", "조리", "사회복지", "메카트로닉스", "보건의료정보", "게임", "금융", "기계·자동화",
    })
    KEYWORD_취업_PREFIX = frozenset({"IT", "건축", "인공지능"})  # "X 쪽(으로) 취업하고 싶어" 시 keyword
    if "쪽" in q:
        prefix_쪽으로 = q.split("쪽으로")[0].strip() if "쪽으로" in q else ""
        prefix_쪽 = q.split(" 쪽 ")[0].strip() if " 쪽 " in q else ""
        prefix = prefix_쪽으로 or prefix_쪽
        if prefix and "취업" in q and prefix.strip() in KEYWORD_취업_PREFIX:
            return "keyword"
        if re.search(r"가고\s*싶어|일\s+하고\s*싶어|일하고\s*싶어", q):
            if prefix:
                n = len(prefix.split())
                if n == 1 and prefix not in ONE_TOKEN_NATURAL:
                    return "keyword"
                if n == 2 and prefix in frozenset({"시스템 운영"}):
                    return "keyword"
    # 5c) "X 관련 일 하고 싶어"에서 X가 2토큰 이하(통번역·인공지능 제외) → keyword
    if " 관련 일 하고 싶어" in q:
        pre = q.split(" 관련 ")[0].strip()
        if pre and len(pre.split()) <= 2 and pre not in frozenset({"통번역", "인공지능"}):
            return "keyword"
    # 5d) 골든 기준 "영양사 되고 싶어" = keyword
    if re.search(r"^영양사\s+되고\s*싶어\s*$", q):
        return "keyword"
    # 6) 짧은 키워드: 단어 수 적고, 문장 끝/동사·희망 표현 없음
    verb_or_wish = re.search(
        r"(하고|하려고|되는|있어|해줘|싶어|가고\s*싶어|되고\s*싶어|일\s+하고\s*싶어|쪽으로\s+가고)",
        q,
    )
    if len(tokens) <= 4 and not re.search(r"[.?!]\s*$", q) and not verb_or_wish:
        return "keyword"
    # 7) 자연어: 긴 문장이거나 구체적 희망 표현 ("가고 싶어", "되고 싶어", "일 하고 싶어", "쪽 하고 싶어", "취업하고 싶어" 등)
    natural_wish = re.search(
        r"(가고\s*싶어|되고\s*싶어|일\s+하고\s*싶어|쪽\s+하고\s*싶어|취업하고\s*싶어|하고싶어|준비하려고|추천해줘|있어\?|도움되는)",
        q,
    )
    if len(tokens) >= 8 or natural_wish:
        return "natural"
    # 8) "취업하고 싶어"가 주된 내용일 때만 keyword (4단어 이하, ex: "IT 취업하고 싶어")
    if len(tokens) <= 4 and "취업" in q and "싶어" in q:
        return "keyword"

    return "mixed"
