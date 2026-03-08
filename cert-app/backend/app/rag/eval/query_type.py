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
    if MAJOR_JOB_PATTERN.search(q) or (MAJOR_OR_JOB_WORDS.search(q) and len(tokens) >= 6):
        return "major+job"
    # 5) 목적만 짧게
    if len(tokens) <= 5 and PURPOSE_ONLY_PATTERN.search(q):
        return "purpose_only"
    # 6) 짧은 키워드
    if len(tokens) <= 4 and not re.search(r"[.?!]\s*$", q) and not re.search(r"(하고|하려고|되는|있어|해줘)", q):
        return "keyword"
    # 7) 긴 자연어
    if len(tokens) >= 8 or re.search(r"(하고싶어|준비하려고|추천해줘|있어\?|도움되는)", q):
        return "natural"

    return "mixed"
