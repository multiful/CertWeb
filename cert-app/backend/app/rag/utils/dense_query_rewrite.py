"""
Dense/vector retrieval 전용 query rewrite.
대화체 질의에서 전공·희망직무·목적 슬롯을 추출해 구조화 문자열로 만든다.
BM25용 expand_query_single_string과 분리된 dense 전용 경로.
추후 LLM 기반 query structuring으로 확장 가능 (use_llm=True).
개인화: profile 인자로 전공/학년/즐겨찾기/취득 자격증을 넣으면 구조화 질의에 반영 (후단 soft score에서 강하게 처리).
실시간 파이프라인에서는
- 1순위: 규칙 기반 _extract_slots
- 2순위: Supabase intent 벡터 테이블을 활용한 라벨 보정
순으로 동작해, 룰이 애매한 케이스만 벡터로 보정한다.
"""
import json
import logging
import re
import time
from typing import Any, Dict, List, Optional, TypedDict

from app.config import get_settings
from app.redis_client import redis_client
from app.rag.utils.domain_tokens import detect_broad_domains_in_text
from app.rag.utils.major_normalize import normalize_major


class UserProfile(TypedDict, total=False):
    """개인화용 사용자 프로필. 모든 필드 선택."""
    major: str
    grade_level: int  # 1~4 학년
    favorite_cert_names: List[str]  # 즐겨찾기(북마크) 자격증명 (재질의에 반영)
    favorite_field_tokens: List[str]  # 즐겨찾기 자격증의 main_field/ncs_large (scoring용)
    acquired_qual_ids: List[int]  # 이미 취득한 qual_id (제외/감점은 후단 scoring)
    acquired_cert_names: List[str]  # 취득 자격증명 (재질의에 반영, 정확도 향상)


# 전공 패턴: "~과", "~학과", "~학부", "~공학", "~학", "~계열"
MAJOR_PATTERNS = [
    r"(\S+과)\s*(?:인데|이고|인데|에\s*다니)",
    r"(\S+학과)\s*(?:인데|이고|에\s*다니)",
    r"(\S+학부)\s*(?:인데|이고|에\s*다니|전공)?",
    r"(\S+공학과?)\s*(?:전공|졸업|재학)",
    r"(\S+학과)\s*(?:전공|졸업|재학)",
    r"(\S+계열)\s*(?:인데|이고|전공)?",
    r"전공\s*[은는]\s*(\S+)",
    r"(\S+)\s*전공",
    r"(\S+학)\s*(?:전공|나왔|나오|졸업)",  # 경영학, 통계학 등
]

# 직무/목적 패턴 (짧은 키워드·직무만 있는 질의 보강)
# "IT 쪽 취업" 등에서 '쪽'만 캡처되지 않도록 'IT 쪽' 전용 패턴을 상단에 둠
JOB_PATTERNS = [
    # 구체 IT 직무/관심 분야
    r"(정보보안)\s*(?:쪽|직무|관련)?",
    r"(보안)\s*쪽",
    r"(네트워크)\s*쪽",
    r"(클라우드)\s*쪽",
    r"(데이터엔지니어)\s*(?:직무|쪽)?",
    r"(데이터\s*엔지니어)\s*(?:직무|쪽)?",
    r"(데이터\s*사이언티스트)",
    r"(데이터\s*사이언스)\s*쪽",
    r"(QA|테스트\s*엔지니어)\s*(?:직무|쪽)?",
    r"(인프라)\s*(?:엔지니어|직무|쪽)?",
    r"(SI\s*개발)\s*(?:쪽|직무)?",
    r"(컨설팅)\s*(?:쪽|직무)?",
    # 기존 패턴
    r"(IT)\s*쪽\s*(?:취업|가고)?",
    r"(정보처리\s*관련?\s*직무)",
    r"(정보처리\s*직무)",
    r"(시스템\s*운영\s*직무)",
    r"(데이터\s*분석\s*직무)",
    r"(데이터\s*분석가)",
    r"(개발\s*직무)",
    r"(개발\s*쪽\s*자격증)",
    r"(개발자)",
    r"(IT\s*직무)",
    r"(IT\s*취업)",
    r"(\S+\s*직무)\s*(?:취업|추천)",  # "IT 직무 취업용", "정보처리 직무"
    r"(\S+직무)\s*(?:로|으로)\s*취업",
    r"(\S+)\s*직무\s*취업",
    r"(\S+)\s*되고\s*싶",
    r"(\S+)\s*취업",
    r"희망\s*직무\s*[은는]?\s*(\S+)",
    r"(데이터\s*쪽)\s*(?:취업|자격증)",
    r"(DB\s*쪽)\s*(?:직무|취업)",
    r"(전산)\s*쪽\s*(?:일|하고|취업|가고)?",  # "전산 쪽 일 하고 싶어" → 희망직무: 전산
    r"(전산\s*직무)",
    r"(개발\s*쪽)",  # "개발 쪽 자격증"
    r"(백엔드)\s*(?:관련|직무|취업)?",
    r"(프론트엔드)\s*(?:관련|직무|취업)?",
    r"(시스템\s*운영)\s*(?:직무)?",  # neither: "시스템 운영 직무 자격증"
    r"(실무\s*쪽)\s*(?:자격증)?",  # "4학년인데 취업용으로 실무 쪽 자격증"
    r"(IT\s*취업\s*준비)",  # "IT 취업 준비 2학년"
    r"(데이터\s*관련\s*직무)",  # "데이터 관련 직무로 가고싶어"
    r"(데이터\s*쪽)\s*(?:자격증|취업)?",  # "데이터 쪽 자격증 추천"
    r"(데이터\s*분석)\s*(?:쪽)?",  # "데이터 분석 쪽 취업 준비"
    r"(뭐\s*따야\s*해)",  # "백엔드 개발자 되려면 뭐 따야 해?"
    r"(되려면)",  # "빅데이터 분석가 되려면"
    r"(전산\s*직무)\s*(?:추천)?",  # "전산 직무 추천 자격증 있어?"
    r"(데이터베이스)\s*(?:랑|과)\s*개발",  # "데이터베이스랑 개발 둘 다"
]
PURPOSE_PATTERNS = [
    r"취업\s*(?:준비|하고\s*싶|을\s*원|용)",
    r"이직\s*(?:준비|을\s*원)",
    r"입문\s*(?:하고\s*싶|을\s*원|용)",
    r"실무\s*용",
    r"실무\s*쪽",  # "취업용으로 실무 쪽 자격증"
    r"커리어\s*시작",
    r"범용성\s*높은",
    r"자격증\s*추천",
    r"도전하고\s*싶어",  # neither: "정처기 땄는데 더 도전하고 싶어"
    r"미리\s*준비",  # "1학년인데 자격증 미리 준비하고 싶어"
    r"준비할\s*만한",  # "정처기 다음으로 준비할 만한 자격증"
    r"다음으로\s*(?:뭘|준비|따면)",  # "컴활 땄는데 다음으로 뭘 따면 좋을까"
    r"다음에\s*뭐\s*따면",  # "ADsP 따놨는데 다음에 뭐 따면 좋아"
    r"뭐\s*따면\s*좋",  # "뭐 따면 좋아"
    r"준비\s*하고\s*있어",  # "데이터 분석 쪽 취업 준비하고 있어"
    r"직무\s*로\s*가려면",  # "IT 직무로 가려면?"
    r"가고\s*싶어",  # "데이터 관련 직무로 가고싶어"
    # 구어체 목적 표현
    r"자격증\s*뭐\s*따",
    r"뭘\s*따야\s*할지",
    r"따면\s*좋을지",
    r"추천해\s*줘",
]

INTEREST_PATTERNS = [
    r"정보처리|IT|개발|데이터|DB|SQL|빅데이터|백엔드|프론트엔드",
    r"간호|의료|회계|금융|전기|전자|기계|건설",
]

BEGINNER_KEYWORDS = ["입문", "입문용", "기초", "처음", "처음 시작", "베이직", "기초부터"]
ADVANCED_KEYWORDS = ["실무", "현업", "심화", "고급", "고난도", "프로젝트", "리더", "실전"]
NEXT_STEP_PATTERNS = ["다음으로", "이후에", "한 단계", "더 어려운"]
MID_CERT_TOKENS = ["ADsP", "데이터분석 준전문가", "정보처리기사", "SQLD"]

# 직무/도메인별 Dense 보조 키워드 매핑.
# Dense-only·vector-only 검색에서 "평균적인 취업 문장"으로 희석되지 않도록,
# 대표 직무에 해당 도메인 자격증 키워드를 강하게 주입한다.
JOB_TO_DENSE_KEYWORDS: Dict[str, List[str]] = {
    # 데이터 분석/데이터 직무 → SQLD/ADsP/빅데이터 키워드 강화
    "데이터 분석": ["데이터 분석 취업 자격증", "SQLD", "ADsP", "데이터분석", "빅데이터분석기사"],
    "데이터분석": ["데이터 분석 취업 자격증", "SQLD", "ADsP", "데이터분석", "빅데이터분석기사"],
    "데이터 엔지니어": ["데이터 엔지니어 취업 자격증", "SQLD", "빅데이터", "빅데이터분석기사"],
    "데이터엔지니어": ["데이터 엔지니어 취업 자격증", "SQLD", "빅데이터", "빅데이터분석기사"],
    # 백엔드/개발 직무 → 정보처리/SQLD 기반 로드맵 강화
    "백엔드": ["백엔드 개발 취업 자격증", "정보처리기사", "SQLD"],
    "개발": ["개발 직무 취업 자격증", "정보처리기사", "SQLD"],
    # 보안 직무 → 정보보안 자격증
    "정보보안": ["정보보안 취업 자격증", "정보보안기사"],
}

def _detect_non_it_domains(slots: Dict[str, str], original: str) -> List[str]:
    """비IT 쿼리에서 도메인 키(관광, 간호, 회계 등)를 감지. BM25 확장 키와 동일한 키 사용."""
    try:
        from app.rag.utils.domain_tokens import get_non_it_bm25_expansion
        expansion = get_non_it_bm25_expansion()
    except Exception:
        return []
    combined = " ".join([
        str(slots.get("전공", "")),
        str(slots.get("희망직무", "")),
        (original or ""),
    ])
    combined = (combined or "").strip()
    detected = []
    for domain_key in expansion.keys():
        if domain_key in combined:
            detected.append(domain_key)
    return detected


def _get_non_it_dense_keywords(slots: Dict[str, str], original: str) -> List[str]:
    """비IT 벡터 쿼리 강화: 도메인별 확장 키워드를 모아 청크와 어휘 겹침을 늘린다."""
    domains = _detect_non_it_domains(slots, original)
    if not domains:
        return []
    try:
        from app.rag.utils.domain_tokens import get_non_it_bm25_expansion
        expansion = get_non_it_bm25_expansion()
    except Exception:
        return []
    keywords = []
    seen = set()
    for key in domains:
        for term in expansion.get(key, []):
            if term not in seen:
                seen.add(term)
                keywords.append(term)
    if keywords:
        keywords.append("자격증")
    return keywords


def _build_dense_boost_terms(
    slots: Dict[str, str],
    original: str,
    profile: Optional[UserProfile] = None,
) -> List[str]:
    """
    Dense/vector 전용 보조 키워드 생성.

    - 비IT 도메인: _get_non_it_dense_keywords 기반 확장.
    - IT/데이터 직무: JOB_TO_DENSE_KEYWORDS 매핑을 통해 대표 자격증 키워드 주입.
    - 프로필: 관심/취득 자격증명을 함께 추가하여 개인화 맥락을 강화.
    """
    original = (original or "").strip()
    terms: List[str] = []

    # 1) 비IT 도메인 확장 키워드 (간호/관광 등)
    terms.extend(_get_non_it_dense_keywords(slots, original))

    # 2) 직무 기반 IT/데이터 키워드
    job = (slots.get("희망직무") or "").strip()
    text_for_match = f"{job} {original}"
    for key, kws in JOB_TO_DENSE_KEYWORDS.items():
        if key and key in text_for_match:
            terms.extend(kws)

    # 3) 프로필 기반 관심 자격증/취득 자격증
    if profile:
        for name in (profile.get("favorite_cert_names") or [])[:5]:
            if name:
                terms.append(str(name))
        for name in (profile.get("acquired_cert_names") or [])[:5]:
            if name:
                terms.append(str(name))

    # 중복 제거 및 길이 제한
    seen: set[str] = set()
    deduped: List[str] = []
    for t in terms:
        t_norm = (t or "").strip()
        if not t_norm or t_norm in seen:
            continue
        seen.add(t_norm)
        deduped.append(t_norm)
        if len(deduped) >= 10:
            break
    return deduped


def _detect_broad_domains_from_slots(
    slots: Dict[str, str],
    original: str,
    profile: Optional[UserProfile] = None,
) -> List[str]:
    """전공/희망직무/프로필 전공/원문을 합쳐 넓은 도메인(IT, 금융, 의료 등)을 감지."""
    parts: List[str] = [
        str(slots.get("전공", "")),
        str(slots.get("희망직무", "")),
    ]
    if profile and profile.get("major"):
        parts.append(str(profile["major"]))
    parts.append(original or "")
    combined = " ".join(p for p in parts if p).strip()
    return detect_broad_domains_in_text(combined)


def _infer_difficulty(
    original: str,
    slots: Dict[str, str],
    profile: Optional[UserProfile] = None,
) -> str:
    """입문/중급/고급 난이도 추론."""
    text = (original or "").strip()
    purpose = (slots.get("목적") or "").strip()
    level = "중급"

    # 1) 입문 신호
    if any(k in text for k in BEGINNER_KEYWORDS):
        return "입문"
    if profile and profile.get("grade_level") in (1, 2):
        acquired = profile.get("acquired_cert_names") or []
        if not acquired and (not purpose or "자격증 추천" in purpose):
            return "입문"

    # 2) 고급 신호
    has_advanced_kw = any(k in text for k in ADVANCED_KEYWORDS)
    has_next_step_kw = any(k in text for k in NEXT_STEP_PATTERNS)
    if profile:
        mid_certs_source: List[str] = []
        mid_certs_source.extend(profile.get("acquired_cert_names") or [])
        mid_certs_source.extend(profile.get("favorite_cert_names") or [])
    else:
        mid_certs_source = []
    has_mid_cert = any(
        token in name for name in mid_certs_source for token in MID_CERT_TOKENS
    )

    if has_advanced_kw or (has_mid_cert and has_next_step_kw):
        return "고급"

    return level


# 재질의 시 IT 계열 보조 키워드(SQLD, 정보처리 등)를 넣을지 판단용.
# data/domain_tokens.json 있으면 Supabase 데이터셋 기반, 없으면 기본값 사용.
def query_suggests_identifier_heavy(text: str) -> bool:
    """
    §2 규칙 4(식별자·코드 보존) 휴리스틱: 코드·NCS형 번호·짧은 영문+숫자 혼합 등이 두드러지면 True.
    확장(HyDE·COT·multi-query 병합 등)을 끄는 스위치와 연동할 때 사용.
    """
    q = (text or "").strip()
    if not q:
        return False
    n = len(q)
    digits = sum(1 for c in q if c.isdigit())
    # NCS·분야코드 형태 (숫자-숫자)
    if re.search(r"\d{2,}\s*[-–]\s*\d{2,}", q):
        return True
    # 짧은 질의에서 숫자 비중이 높음 (수험번호·연도 혼합 등)
    if n <= 64 and digits >= 4 and (digits / max(n, 1)) >= 0.18:
        return True
    # 영문 약어+숫자 (예: ADsP, SQLP, NCS 등)
    if n <= 48 and re.search(r"[A-Za-z]{2,}\s*\d|\d\s*[A-Za-z]{2,}|[A-Z]{2,}\d+", q):
        return True
    return False


def _query_suggests_it_domain(slots: Dict[str, str], original: str) -> bool:
    """쿼리나 슬롯이 IT/데이터 계열로 보이면 True. BM25_BASELINE_MODE=1이면 항상 True(기존 동작)."""
    import os
    if os.environ.get("BM25_BASELINE_MODE") == "1":
        return True
    from app.rag.utils.domain_tokens import get_it_tokens, get_non_it_tokens
    it_tokens = get_it_tokens()
    non_it_tokens = get_non_it_tokens()
    combined = " ".join([str(slots.get("전공", "")), str(slots.get("희망직무", "")), original or ""])
    combined = (combined or "").strip()
    for t in non_it_tokens:
        if t in combined:
            return False
    for t in it_tokens:
        if t in combined:
            return True
    return False


def _extract_slots(query: str) -> Dict[str, str]:
    """규칙 기반으로 전공/희망직무/목적 슬롯 추출."""
    q = (query or "").strip()
    slots: Dict[str, str] = {
        "전공": "",
        "희망직무": "",
        "목적": "",
        "학년": "",  # "N학년" 추출 (profile 없어도 구조화에 반영)
    }
    if not q:
        return slots

    # 학년: "1학년", "2학년", "4학년" 등 (neither 쿼리 보강)
    grade_m = re.search(r"([1-4])\s*학년", q)
    if grade_m:
        slots["학년"] = f"{grade_m.group(1)}학년"

    for pattern in MAJOR_PATTERNS:
        m = re.search(pattern, q, re.IGNORECASE)
        if m:
            slots["전공"] = normalize_major(m.group(1).strip())
            break
    if not slots["전공"]:
        # 전공 폴백: 자주 등장하는 학과/계열 키워드
        fallback_majors = [
            "산업데이터공학과",
            "AI데이터공학과",
            "AI빅데이터학과",
            "컴퓨터공학",
            "컴퓨터공학과",
            "컴퓨터정보과",
            "소프트웨어학과",
            "소프트웨어공학과",
            "정보통신",
            "정보보안",
            "경영학",
            "통계학",
        ]
        for token in fallback_majors:
            if token in q:
                slots["전공"] = normalize_major(token)
                break

    for pattern in JOB_PATTERNS:
        m = re.search(pattern, q)
        if m:
            slots["희망직무"] = m.group(1).strip()
            break
    if not slots["희망직무"] and "직무" in q:
        idx = q.find("직무")
        start = max(0, idx - 12)
        slots["희망직무"] = q[start:idx + 6].strip()
    if not slots["희망직무"] and ("데이터 관련" in q or "데이터 쪽" in q):
        slots["희망직무"] = "데이터 분석"
    if not slots["희망직무"] and "ADsP" in q and "다음에 뭐 따면" in q:
        # ADsP 이후 로드맵 질의: 데이터 분석 직무/로드맵으로 본다.
        slots["희망직무"] = "데이터 분석"
    if not slots["희망직무"] and ("되려면" in q or "뭐 따야" in q):
        for token in ["백엔드", "개발자", "빅데이터", "분석가"]:
            if token in q:
                slots["희망직무"] = "백엔드 개발" if "백엔드" in q or "개발자" in q else ("빅데이터 분석" if "빅데이터" in q or "분석가" in q else token)
                break
    if not slots["희망직무"] and ("가려면" in q or "가고 싶어" in q or "가고싶어" in q) and "직무" in q:
        slots["희망직무"] = "IT 직무" if "IT" in q else "데이터 분석"

    # 일반적인 "X 관련 일 하고 싶어" 패턴 (통번역/인공지능/3D 조형/사무·경영 등)
    if not slots["희망직무"]:
        m = re.search(r"(\S+)\s*관련\s*일\s*하고\s*싶", q)
        if m:
            slots["희망직무"] = m.group(1).strip()

    # 일반적인 "X 쪽으로/쪽 일/쪽 가고 싶어" 패턴 (도메인 전체를 희망 직무로 사용)
    if not slots["희망직무"]:
        m = re.search(r"(\S+)\s*쪽\s*(?:일|으로|가고|취업|하고)?", q)
        if m:
            slots["희망직무"] = m.group(1).strip()

    # 조사까지 함께 캡처된 경우(예: "데이터베이스나 개발 쪽" → "데이터베이스나") 및
    # "쪽/쪽으로"만 남는 비의미적 희망직무 후처리
    if slots["희망직무"]:
        job = slots["희망직무"]
        # 대표적인 조사 '나', '이나' 제거
        for suffix in ("이나", "나"):
            if job.endswith(suffix) and len(job) > len(suffix):
                job = job[: -len(suffix)]
                break
        # 뒤에 붙은 '쪽' / '쪽으로' 제거 (예: "인공지능 쪽", "인공지능 쪽으로")
        job_norm = re.sub(r"\s*쪽(?:으로)?$", "", job).strip()
        # "쪽" / "쪽으로"만 남은 경우는 의미 없는 값이므로 비움
        if job_norm in {"", "쪽", "쪽으로"}:
            slots["희망직무"] = ""
        else:
            slots["희망직무"] = job_norm

    for p in PURPOSE_PATTERNS:
        if re.search(p, q):
            if "취업" in p or "취업" in q:
                slots["목적"] = "취업 준비"
            elif "이직" in p or "이직" in q:
                slots["목적"] = "이직 준비"
            elif "입문" in p:
                slots["목적"] = "입문"
            elif "실무" in p:
                slots["목적"] = "실무"
            elif "커리어" in p:
                slots["목적"] = "취업 준비"
            elif "범용성" in p:
                slots["목적"] = "자격증 추천"
            else:
                slots["목적"] = "자격증 추천"
            break
    if not slots["목적"] and ("취업" in q or "추천" in q):
        slots["목적"] = "취업 준비" if "취업" in q else "자격증 추천"
    if not slots["목적"] and ("취업용" in q or "입문용" in q or "실무용" in q or "실무 쪽" in q):
        if "취업용" in q or "취업" in q:
            slots["목적"] = "취업 준비"
        elif "입문용" in q:
            slots["목적"] = "입문"
        elif "실무" in q:
            slots["목적"] = "실무"
        else:
            slots["목적"] = "취업 준비"
    if not slots["목적"] and ("도전" in q or "준비하고 싶어" in q or "미리 준비" in q or "조금 더 어려운 걸 해보고 싶어" in q):
        # "조금 더 어려운 걸 해보고 싶어" 같은 표현은 기존 자격 이후 심화/상위 자격 추천 요청
        # 이 경우도 학습 데이터와 파이프라인에서는 자격증 추천으로 본다.
        slots["목적"] = "자격증 추천"
    if not slots["목적"] and ("준비하고 있어" in q or "가려면" in q):
        slots["목적"] = "취업 준비" if "취업" in q or "직무" in q else "자격증 추천"
    # 직업/직무명을 언급하면서 "~되고 싶어", "~일 하고 싶어"로 끝나는 경우는 취업 목적일 가능성이 높음
    if not slots["목적"]:
        if ("되고 싶어" in q or "되고싶어" in q or "일 하고 싶어" in q or "일하고 싶어" in q):
            slots["목적"] = "취업 준비"
        # "~하고 싶어" 이면서 '쪽' 또는 '일' 같은 표현이 함께 나오면 역시 취업 목적일 가능성이 큼
        elif "하고 싶어" in q or "하고싶어" in q:
            if "쪽" in q or "일" in q or "취업" in q:
                slots["목적"] = "취업 준비"

    return slots


DENSE_REWRITE_FIXED_KEYS = ["전공", "희망직무", "목적"]


logger = logging.getLogger(__name__)
_settings = get_settings()
_LOCAL_QT_CACHE: Dict[str, tuple[float, Optional[str]]] = {}
_LOCAL_QT_CACHE_MAX = 2048


def _local_qt_cache_get(key: str, ttl_s: int) -> tuple[bool, Optional[str]]:
    """프로세스 로컬 query_type 캐시 조회. Redis 미연결 시 DB 왕복 완화용."""
    if not key:
        return False, None
    row = _LOCAL_QT_CACHE.get(key)
    if not row:
        return False, None
    ts, qt = row
    if (time.time() - ts) > max(1, ttl_s):
        _LOCAL_QT_CACHE.pop(key, None)
        return False, None
    return True, qt


def _local_qt_cache_set(key: str, qt: Optional[str]) -> None:
    if not key:
        return
    _LOCAL_QT_CACHE[key] = (time.time(), qt)
    if len(_LOCAL_QT_CACHE) > _LOCAL_QT_CACHE_MAX:
        # 오래된 절반 정리 (간단 LRU 근사)
        oldest = sorted(_LOCAL_QT_CACHE.items(), key=lambda kv: kv[1][0])[: _LOCAL_QT_CACHE_MAX // 2]
        for k, _ in oldest:
            _LOCAL_QT_CACHE.pop(k, None)


def _dense_cache_hash(q: str, profile: Optional[UserProfile]) -> str:
    """
    Redis 재질의/슬롯 캐시 키용 해시.

    - 프로필이 **없거나 빈 dict** (`None`, `{}`): 과거와 동일하게 **질문 q만** 해시 → 불필요한 캐시 미스·추가 직렬화 비용 방지.
    - 프로필에 값이 있으면: 동일 질문이라도 재질의·슬롯이 달라지므로 `profile`을 포함해 분리한다.
    """
    qn = (q or "").strip()
    try:
        if not profile:
            return redis_client.hash_query_params(q=qn)
        return redis_client.hash_query_params(
            q=qn,
            profile=json.dumps(profile, sort_keys=True, default=str),
        )
    except Exception:
        return redis_client.hash_query_params(q=qn)


def _apply_intent_vector_fallback(slots: Dict[str, str], original: str) -> Dict[str, str]:
    """
    규칙 기반 슬롯 추출 이후, 희망직무/목적이 비어 있거나 애매한 경우
    Supabase intent_labels 테이블(쿼리 임베딩 ↔ 라벨 임베딩 유사도)로 보정한다.

    - job(희망직무): 비어 있거나 포괄적일 때만 보정
    - purpose(목적): 비어 있을 때만 보정
    """
    q = (original or "").strip()
    if not q:
        return slots

    missing_job = not (slots.get("희망직무") or "").strip()
    # "쪽"만 나온 경우(예: "IT 쪽 취업"에서 \S+ 취업이 '쪽' 캡처) intent로 보정
    generic_job = slots.get("희망직무") in {"IT 직무", "개발", "데이터 분석", "쪽"}
    need_job = missing_job or generic_job

    missing_purpose = not (slots.get("목적") or "").strip()
    need_purpose = missing_purpose

    if not (need_job or need_purpose):
        return slots

    try:
        from app.rag.utils.intent_vector_labels import lookup_intent_labels_with_vector
    except Exception:
        logger.debug("intent_vector_fallback: import failed (intent lookup disabled?)", exc_info=True)
        return slots

    kinds: List[str] = []
    if need_job:
        kinds.append("job")
    if need_purpose:
        kinds.append("purpose")
    if not kinds:
        return slots

    try:
        intent_labels = lookup_intent_labels_with_vector(q, kinds=kinds, top_k=1)
    except Exception:
        logger.debug("intent_vector_fallback: lookup failed", exc_info=True)
        return slots

    if need_job and intent_labels.get("job"):
        slots["희망직무"] = intent_labels["job"]
    if need_purpose and intent_labels.get("purpose"):
        slots["목적"] = intent_labels["purpose"]

    return slots


def _apply_dense_slot_vector_fallback(
    slots: Dict[str, str], original: str, _profile: Optional[UserProfile] = None
) -> Dict[str, str]:
    """
    intent_vector_fallback 이후, dense_slot_labels 테이블(쿼리 임베딩 ↔ 슬롯 라벨 유사도)로
    희망직무/목적을 추가 보정. RAG_DENSE_SLOT_VECTOR_FALLBACK_ENABLE=True 일 때만 동작.

    - job: 비어 있거나 포괄적(IT 직무, 개발, 데이터 분석, 쪽)일 때만 보정
    - purpose: 비어 있거나 "자격증 추천"일 때만 보정
    """
    q = (original or "").strip()
    if not q:
        return slots

    try:
        from app.rag.utils.slot_vector_labels import lookup_slot_label_with_vector
    except Exception:
        logger.debug("dense_slot_vector_fallback: import failed", exc_info=True)
        return slots

    missing_job = not (slots.get("희망직무") or "").strip()
    generic_job = (slots.get("희망직무") or "").strip() in {"IT 직무", "개발", "데이터 분석", "쪽"}
    if missing_job or generic_job:
        try:
            label = lookup_slot_label_with_vector(q, "job", top_k=1)
            if label:
                slots["희망직무"] = label
        except Exception:
            logger.debug("dense_slot_vector_fallback: job lookup failed", exc_info=True)

    missing_purpose = not (slots.get("목적") or "").strip()
    generic_purpose = (slots.get("목적") or "").strip() == "자격증 추천"
    if missing_purpose or generic_purpose:
        try:
            label = lookup_slot_label_with_vector(q, "purpose", top_k=1)
            if label:
                slots["목적"] = label
        except Exception:
            logger.debug("dense_slot_vector_fallback: purpose lookup failed", exc_info=True)

    return slots


def _slots_from_rewrite_pipeline(
    q: str,
    profile: Optional[UserProfile] = None,
) -> Dict[str, str]:
    """
    재질의(rewrite_for_dense)와 동일한 슬롯 파이프라인.
    규칙 추출 → intent 벡터 보정 → dense_slot 벡터 보정 → 프로필 병합.
    """
    slots = _extract_slots(q)
    try:
        slots = _apply_intent_vector_fallback(slots, q)
    except Exception:
        logger.debug("slots_from_rewrite_pipeline: intent_vector_fallback failed", exc_info=True)
    try:
        slots = _apply_dense_slot_vector_fallback(slots, q, profile)
    except Exception:
        logger.debug("slots_from_rewrite_pipeline: dense_slot_vector_fallback failed", exc_info=True)
    slots = _merge_profile_into_slots(slots, profile)
    return slots


def _annotate_domain_difficulty_in_slots(
    slots: Dict[str, str],
    original: str,
    profile: Optional[UserProfile] = None,
) -> None:
    """
    _slots_to_structured_text / 메타 soft와 동일한 도메인·난이도 규칙을 slots에 in-place 반영.
    (벡터 fallback 옵션 포함 — 구조화 문자열과 동일 로직)
    """
    original = (original or "").strip()
    domains = _detect_broad_domains_from_slots(slots, original, profile=profile)
    if not domains:
        try:
            from app.rag.config import get_rag_settings

            if get_rag_settings().RAG_DENSE_SLOT_VECTOR_FALLBACK_ENABLE:
                from app.rag.utils.slot_vector_labels import lookup_slot_label_with_vector

                v = lookup_slot_label_with_vector(original, "domain", top_k=1)
                if v:
                    domains = [s.strip() for s in v.split(",") if s.strip()] or [v]
        except Exception:
            pass
    domain_line = ", ".join(domains) if domains else "없음"
    slots["도메인"] = domain_line
    # 정규화도메인: 세부 도메인을 기준으로 상위 도메인(top_domain)으로 매핑.
    # 예) 선박/해양 -> 모빌리티/운송
    normalized_domains: List[str] = []
    if domains:
        try:
            from app.rag.utils.domain_tokens import get_top_domain_for_domain

            seen_top = set()
            for d in domains:
                top = (get_top_domain_for_domain(d) or "").strip()
                if not top:
                    continue
                if top in seen_top:
                    continue
                seen_top.add(top)
                normalized_domains.append(top)
        except Exception:
            normalized_domains = []
    slots["정규화도메인"] = ", ".join(normalized_domains) if normalized_domains else "없음"

    # 희망직무는 비어 있지 않도록 보강한다.
    # - 1순위: 도메인
    # - 2순위: 전공
    # - 3순위: 일반 fallback
    job = (slots.get("희망직무") or "").strip()
    if not job:
        if domains:
            slots["희망직무"] = domains[0]
        elif (slots.get("전공") or "").strip():
            slots["희망직무"] = (slots.get("전공") or "").strip()
        else:
            slots["희망직무"] = "관련 직무"

    difficulty = _infer_difficulty(original, slots, profile=profile)
    if difficulty == "중급":
        try:
            from app.rag.config import get_rag_settings

            if get_rag_settings().RAG_DENSE_SLOT_VECTOR_FALLBACK_ENABLE:
                from app.rag.utils.slot_vector_labels import lookup_slot_label_with_vector

                v = lookup_slot_label_with_vector(original, "difficulty", top_k=1)
                if v:
                    difficulty = v
        except Exception:
            pass
    slots["난이도"] = difficulty


def _slots_to_structured_text(
    slots: Dict[str, str],
    original: str,
    profile: Optional[UserProfile] = None,
) -> str:
    """
    슬롯을 Dense/Vector 검색용 구조화 문자열로 변환.

    필드 출력 정책:
    ┌─────────────────┬──────────────────────────────────────┐
    │ 필드            │ 정책                                 │
    ├─────────────────┼──────────────────────────────────────┤
    │ 전공            │ 항상 출력 (값이 없으면 생략)          │
    │ 학년            │ 항상 출력 — NULL이면 "없음"          │
    │ 도메인          │ 값이 있을 때만                        │
    │ 난이도          │ "중급"(기본값) 제외, 입문/고급만     │
    │ 희망직무        │ 값이 있을 때만 (parsing 실패 생략)    │
    │ 관심 자격증     │ 항상 출력 — 없으면 "없음"            │
    │ 취득 자격증     │ 항상 출력 — 없으면 "없음"            │
    │ 목적            │ 값이 있을 때만 (generic 제외)         │
    │ 키워드(boost)   │ 값이 있을 때만, cert 반복 허용       │
    │ 질문(원문)      │ 항상 마지막에 출력                    │
    └─────────────────┴──────────────────────────────────────┘

    학년/관심자격증/취득자격증을 "없음"으로 출력하는 이유:
    "없음"은 "사용자에게 해당 정보가 없다"는 의미 있는 NULL 신호.
    필드 자체가 없으면 이 신호를 잃는다.
    """
    original = (original or "").strip()
    lines: List[str] = []

    # 1. 전공 (값 있을 때만)
    raw_major = ((profile.get("major") if profile else "") or "").strip()
    major = (slots.get("전공") or "").strip() or raw_major
    if raw_major and major and raw_major != major:
        major_display = f"{raw_major} ({major})"
    else:
        major_display = major or raw_major
    if major_display:
        lines.append("전공: " + major_display)

    # 2. 학년 — NULL이어도 항상 출력 ("없음" 자체가 정보)
    grade_str = (slots.get("학년") or "").strip()
    if not grade_str and profile and profile.get("grade_level") is not None:
        try:
            g = int(profile["grade_level"])
            if 1 <= g <= 4:
                grade_str = f"{g}학년"
        except (TypeError, ValueError):
            pass
    lines.append("학년: " + (grade_str if grade_str else "없음"))

    # 3. 도메인 (값 있을 때만)
    _annotate_domain_difficulty_in_slots(slots, original, profile=profile)
    domain_line = (slots.get("도메인") or "").strip()
    if domain_line and domain_line != "없음":
        lines.append("도메인: " + domain_line)

    # 4. 난이도: "중급"(기본값, 구별력 없음) 생략
    difficulty = (slots.get("난이도") or "중급").strip()
    if difficulty and difficulty != "중급":
        lines.append("난이도: " + difficulty)

    # 5. 희망직무 (parsing 성공 시만, placeholder 제거)
    job = (slots.get("희망직무") or "").strip()
    if job:
        lines.append("희망직무: " + job)

    # 6. 관심 자격증 — NULL이어도 항상 출력 ("없음" 자체가 정보)
    favorite_names = (profile.get("favorite_cert_names") or [])[:5] if profile else []
    lines.append(
        "관심 자격증: " + (", ".join(favorite_names) if favorite_names else "없음")
    )

    # 7. 취득 자격증 — NULL이어도 항상 출력 ("없음" 자체가 정보)
    acquired_names = (profile.get("acquired_cert_names") or [])[:10] if profile else []
    lines.append(
        "취득 자격증: " + (", ".join(acquired_names) if acquired_names else "없음")
    )

    # 8. 목적: 값이 있을 때만 출력
    purpose = (slots.get("목적") or "").strip()
    if purpose:
        lines.append("목적: " + purpose)

    # 9. 보조 키워드 — cert 이름 반복 허용 (임베딩 가중치 강화)
    dense_boost_terms = _build_dense_boost_terms(slots, original, profile=profile)
    if dense_boost_terms:
        lines.append("키워드: " + " ".join(dense_boost_terms))

    # 10. 질문(원문) — 항상 마지막 (구조화 슬롯 + 원문 문맥 동시 제공)
    if original:
        lines.append("질문: " + original)

    return "\n".join(lines)


def _rewrite_for_dense_core(
    q: str,
    profile: Optional[UserProfile] = None,
) -> tuple[str, Dict[str, Any]]:
    """
    재질의 문자열 + 메타 soft/리랭커용 슬롯 dict(도메인·난이도 포함)를 한 번에 계산.
    hybrid_retrieve에서 extract_slots_for_dense 중복 호출을 막기 위해 사용한다.
    """
    base = _slots_from_rewrite_pipeline(q, profile)
    slots_copy = dict(base)
    rewritten = _slots_to_structured_text(slots_copy, q, profile=profile)
    scoring_slots: Dict[str, Any] = dict(slots_copy)
    return rewritten, scoring_slots


def rewrite_for_dense(
    query: str,
    use_llm: bool = False,
    profile: Optional[UserProfile] = None,
) -> str:
    """
    Dense retrieval용 질의 재작성.
    규칙 기반으로 슬롯 추출 후 구조화 문자열 반환.
    profile이 있으면 전공/학년/관심 자격증/취득 여부를 구조화 문자열에 반영 (개인화).
    use_llm=True는 추후 LLM 기반 구현용 예약.
    """
    if use_llm:
        # TODO: LLM 기반 query structuring
        pass
    q = (query or "").strip()
    if not q:
        return q
    # 규칙 기반 rewrite는 순수 파이썬이지만, intent-vector 보정 등과 결합되면
    # 재질의에서 불필요한 계산이 반복될 수 있으므로 Redis에 TTL 캐시를 둔다.
    # v4 문자열 / v6 번들: 학년·관심자격증·취득자격증 항상 출력 + 질문 마지막 구조 반영.
    cache_key: Optional[str] = None
    h = ""
    if redis_client.is_connected():
        try:
            h = _dense_cache_hash(q, profile)
            cache_key = f"rag:dense_rewrite:v4:{h}"
            cached = redis_client.get(cache_key)
            if isinstance(cached, str):
                return cached
        except Exception:
            cache_key = None
    rewritten, scoring_slots = _rewrite_for_dense_core(q, profile)
    if cache_key and h:
        try:
            redis_client.set(cache_key, rewritten, ttl=_settings.CACHE_TTL_RAG)
            redis_client.set(
                f"rag:dense_bundle:v6:{h}",
                {"rewrite": rewritten, "slots": scoring_slots},
                ttl=_settings.CACHE_TTL_RAG,
            )
        except Exception:
            pass
    return rewritten


def _merge_profile_into_slots(slots: Dict[str, str], profile: Optional[UserProfile]) -> Dict[str, str]:
    """프로필이 있으면 전공/학년을 슬롯에 반영. 쿼리에서 추출한 값이 없을 때만 채운다."""
    if not profile:
        return slots
    if not (slots.get("전공") or "").strip() and profile.get("major"):
        slots["전공"] = normalize_major((profile["major"] or "").strip())
    if not (slots.get("학년") or "").strip() and profile.get("grade_level") is not None:
        try:
            g = int(profile["grade_level"])
            if 1 <= g <= 4:
                slots["학년"] = f"{g}학년"
        except (TypeError, ValueError):
            pass
    return slots


def rewrite_and_slots_for_dense(
    query: str,
    profile: Optional[UserProfile] = None,
    use_intent_fallback: bool = True,
) -> tuple:
    """
    재질의 문자열과 슬롯을 함께 반환. profile이 있으면 전공/학년을 슬롯에 반영.
    스냅샷 생성·평가용. (캐시 미사용)
    반환: (rewrite: str, slots: Dict[str, str])
    """
    q = (query or "").strip()
    if not use_intent_fallback:
        slots = _extract_slots(q)
        try:
            slots = _apply_dense_slot_vector_fallback(slots, q, profile)
        except Exception:
            pass
        slots = _merge_profile_into_slots(slots, profile)
    else:
        slots = _slots_from_rewrite_pipeline(q, profile)
    rewrite = _slots_to_structured_text(slots, q, profile=profile)
    return (rewrite, dict(slots))


def rewrite_for_dense_with_type(
    query: str,
    profile: Optional[UserProfile] = None,
) -> tuple[str, Optional[str], Optional[Dict[str, Any]]]:
    """
    Dense 재질의 문자열, query_type, 그리고 메타 soft용 슬롯 dict를 함께 반환.

    세 번째 값은 재질의와 동일 슬롯 파이프라인으로 계산된다.
    Redis `rag:dense_bundle:v7:*` 히트 시 재질의+슬롯+query_type을 함께 복원하고,
    v6 번들(rewrite+slots) 또는 v4 문자열 캐시 순으로 fallback한다.

    query_type은 우선적으로 Supabase query_type_labels 벡터 테이블에서
    raw_query(+프로필) 기반으로 조회하고, 실패 시 기존 rule-based
    classify_query_type을 fallback으로 사용한다.
    """
    q = (query or "").strip()
    if not q:
        return q, None, None

    # v4 문자열 / v6 번들(rewrite+slots) / v7 번들(rewrite+slots+qt)
    # 포맷 변경 이력: v4 = 학년·관심·취득자격증 항상 출력, 질문 마지막
    cache_key_v4: Optional[str] = None
    bundle_key_v7: Optional[str] = None
    qt_cache_key: Optional[str] = None
    h = ""
    if redis_client.is_connected():
        try:
            h = _dense_cache_hash(q, profile)
            cache_key_v4 = f"rag:dense_rewrite:v4:{h}"
            bundle_key_v7 = f"rag:dense_bundle:v7:{h}"
            qt_cache_key = f"rag:dense_qt:v1:{h}"
            bundle_v7 = redis_client.get(bundle_key_v7)
            if (
                isinstance(bundle_v7, dict)
                and bundle_v7.get("rewrite") is not None
                and isinstance(bundle_v7.get("slots"), dict)
                and ("qt" in bundle_v7)
            ):
                return str(bundle_v7["rewrite"]), (bundle_v7.get("qt") or None), dict(bundle_v7["slots"])
            key_v6 = f"rag:dense_bundle:v6:{h}"
            bundle = redis_client.get(key_v6)
            if (
                isinstance(bundle, dict)
                and bundle.get("rewrite") is not None
                and isinstance(bundle.get("slots"), dict)
            ):
                rewrite = str(bundle["rewrite"])
                scoring_slots = dict(bundle["slots"])
            else:
                cached_v4 = redis_client.get(cache_key_v4)
                if isinstance(cached_v4, str):
                    rewrite = cached_v4
                    scoring_slots = extract_slots_for_dense(q, profile)
                else:
                    rewrite, scoring_slots = _rewrite_for_dense_core(q, profile)
                    try:
                        redis_client.set(cache_key_v4, rewrite, ttl=_settings.CACHE_TTL_RAG)
                        redis_client.set(
                            key_v6,
                            {"rewrite": rewrite, "slots": scoring_slots},
                            ttl=_settings.CACHE_TTL_RAG,
                        )
                    except Exception:
                        pass
        except Exception:
            rewrite, scoring_slots = _rewrite_for_dense_core(q, profile)
            if h and cache_key_v4:
                try:
                    redis_client.set(cache_key_v4, rewrite, ttl=_settings.CACHE_TTL_RAG)
                    redis_client.set(
                        f"rag:dense_bundle:v6:{h}",
                        {"rewrite": rewrite, "slots": scoring_slots},
                        ttl=_settings.CACHE_TTL_RAG,
                    )
                except Exception:
                    pass
    else:
        rewrite, scoring_slots = _rewrite_for_dense_core(q, profile)

    # 1) query_type 캐시 확인 (질문+프로필 해시)
    qt: Optional[str] = None
    qt_cached = False
    if redis_client.is_connected() and qt_cache_key:
        try:
            cached_qt = redis_client.get(qt_cache_key)
            if isinstance(cached_qt, str):
                qt_cached = True
                qt = None if cached_qt == "__NONE__" else cached_qt
        except Exception:
            qt = None
    # Redis가 없거나 캐시 미스면 로컬 캐시 사용
    if not qt_cached and qt_cache_key:
        hit, local_qt = _local_qt_cache_get(qt_cache_key, int(_settings.CACHE_TTL_RAG))
        if hit:
            qt_cached = True
            qt = local_qt

    # 2) 캐시 미스 시 Supabase query_type_labels 벡터 매칭 시도
    if not qt_cached:
        try:
            from app.rag.utils.query_type_vector_labels import lookup_query_type_with_vector

            major = profile.get("major") if profile else None
            grade_level = profile.get("grade_level") if profile else None
            qt = lookup_query_type_with_vector(q, major=major, grade_level=grade_level)
        except Exception:
            qt = None

    # 3) 실패 시 기존 rule-based query_type 분류로 fallback
    if not qt:
        try:
            from app.rag.eval.query_type import classify_query_type

            qt = classify_query_type(q, from_golden=None)
        except Exception:
            qt = None
    if redis_client.is_connected() and qt_cache_key:
        try:
            redis_client.set(
                qt_cache_key,
                qt if qt else "__NONE__",
                ttl=_settings.CACHE_TTL_RAG,
            )
        except Exception:
            pass
    if qt_cache_key:
        _local_qt_cache_set(qt_cache_key, qt)

    # 선택: 재질의 문자열에 쿼리유형 추가 (벡터/contrastive 입력 품질·리랭커 학습 일치용)
    try:
        from app.rag.config import get_rag_settings

        if get_rag_settings().RAG_REWRITE_ADD_QUERY_TYPE and qt:
            rewrite = rewrite + "\n쿼리유형: " + qt
    except Exception:
        pass

    # 최종 결과(v7) 캐시: rewrite/slots/query_type
    if redis_client.is_connected() and bundle_key_v7:
        try:
            redis_client.set(
                bundle_key_v7,
                {"rewrite": rewrite, "slots": scoring_slots, "qt": qt},
                ttl=_settings.CACHE_TTL_RAG,
            )
        except Exception:
            pass
    return rewrite, qt, scoring_slots


def extract_slots_for_dense(query: str, profile: Optional[UserProfile] = None) -> Dict[str, Any]:
    """
    메타 soft / 리랭커 등에서 사용하는 슬롯 dict.
    재질의(rewrite_for_dense)와 동일 파이프라인(intent·dense_slot 보정 포함) 후
    도메인·난이도를 구조화 경로와 동일 규칙으로 채운다.
    """
    q = (query or "").strip()
    if not q:
        return {}
    base = _slots_from_rewrite_pipeline(q, profile)
    slots_copy: Dict[str, Any] = dict(base)
    _annotate_domain_difficulty_in_slots(slots_copy, q, profile=profile)
    return slots_copy
