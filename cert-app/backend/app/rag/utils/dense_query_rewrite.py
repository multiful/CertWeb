"""
Dense/vector retrieval 전용 query rewrite.
대화체 질의에서 전공·희망직무·목적·관심분야·원하는 결과 슬롯을 추출해 구조화 문자열로 만든다.
BM25용 expand_query_single_string과 분리된 dense 전용 경로.
추후 LLM 기반 query structuring으로 확장 가능 (use_llm=True).
개인화: profile 인자로 전공/학년/즐겨찾기/취득 자격증을 넣으면 구조화 질의에 반영 (후단 soft score에서 강하게 처리).
"""
import re
from typing import Any, Dict, List, Optional, TypedDict


class UserProfile(TypedDict, total=False):
    """개인화용 사용자 프로필. 모든 필드 선택."""
    major: str
    grade_level: int  # 1~4 학년
    favorite_cert_names: List[str]  # 즐겨찾기(북마크) 자격증명 (재질의에 반영)
    favorite_field_tokens: List[str]  # 즐겨찾기 자격증의 main_field/ncs_large (scoring용)
    acquired_qual_ids: List[int]  # 이미 취득한 qual_id (제외/감점은 후단 scoring)
    acquired_cert_names: List[str]  # 취득 자격증명 (재질의에 반영, 정확도 향상)


# 전공 패턴: "~과", "~학과", "~공학", "~학"
MAJOR_PATTERNS = [
    r"(\S+과)\s*(?:인데|이고|인데|에\s*다니)",
    r"(\S+학과)\s*(?:인데|이고|에\s*다니)",
    r"(\S+공학과?)\s*(?:전공|졸업|재학)",
    r"(\S+학과)\s*(?:전공|졸업|재학)",
    r"전공\s*[은는]\s*(\S+)",
    r"(\S+)\s*전공",
]

# 직무/목적 패턴 (짧은 키워드·직무만 있는 질의 보강)
JOB_PATTERNS = [
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
    r"준비\s*하고\s*있어",  # "데이터 분석 쪽 취업 준비하고 있어"
    r"직무\s*로\s*가려면",  # "IT 직무로 가려면?"
    r"가고\s*싶어",  # "데이터 관련 직무로 가고싶어"
]
INTEREST_PATTERNS = [
    r"정보처리|IT|개발|데이터|DB|SQL|빅데이터|백엔드|프론트엔드",
    r"간호|의료|회계|금융|전기|전자|기계|건설",
]


def _extract_slots(query: str) -> Dict[str, str]:
    """규칙 기반으로 전공/희망직무/목적/관심분야/원하는 결과 슬롯 추출."""
    q = (query or "").strip()
    slots: Dict[str, str] = {
        "전공": "",
        "희망직무": "",
        "목적": "",
        "관심분야": "",
        "원하는_결과": "",
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
            slots["전공"] = m.group(1).strip()
            break
    if not slots["전공"]:
        for token in ["산업데이터공학과", "컴퓨터공학", "소프트웨어학과", "정보통신", "경영학", "통계학"]:
            if token in q:
                slots["전공"] = token
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
    if not slots["희망직무"] and ("되려면" in q or "뭐 따야" in q):
        for token in ["백엔드", "개발자", "빅데이터", "분석가"]:
            if token in q:
                slots["희망직무"] = "백엔드 개발" if "백엔드" in q or "개발자" in q else ("빅데이터 분석" if "빅데이터" in q or "분석가" in q else token)
                break
    if not slots["희망직무"] and ("가려면" in q or "가고 싶어" in q or "가고싶어" in q) and "직무" in q:
        slots["희망직무"] = "IT 직무" if "IT" in q else "데이터 분석"

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
    if not slots["목적"] and ("도전" in q or "준비하고 싶어" in q or "미리 준비" in q):
        slots["목적"] = "자격증 추천"
    if not slots["목적"] and ("준비하고 있어" in q or "가려면" in q):
        slots["목적"] = "취업 준비" if "취업" in q or "직무" in q else "자격증 추천"

    interest_parts = []
    for p in INTEREST_PATTERNS:
        for m in re.finditer(p, q):
            interest_parts.append(m.group(0))
    if interest_parts:
        slots["관심분야"] = ", ".join(dict.fromkeys(interest_parts))
    if not slots["관심분야"] and slots["희망직무"]:
        slots["관심분야"] = slots["희망직무"]
    # "시스템 운영 직무" 등: 벡터 문서에 정보처리/IT가 많으므로 관심분야 보강
    if slots.get("희망직무") and ("시스템" in slots["희망직무"] or "운영" in slots["희망직무"]):
        slots["관심분야"] = (slots.get("관심분야") or "") + " 정보처리 IT" if slots.get("관심분야") else "시스템 운영 정보처리 IT"
    if not slots["관심분야"] and slots["전공"]:
        slots["관심분야"] = slots["전공"]
    if not slots["관심분야"] and ("데이터베이스" in q and "개발" in q):
        slots["관심분야"] = "데이터베이스, 개발, SQL, SQLD"
    # 짧은 키워드 질의: 직무/전공 없어도 관심분야만 추론 (예: "IT 직무 취업용", "데이터 쪽 취업")
    if not slots["관심분야"] and q:
        for token in ["IT", "데이터", "정보처리", "개발", "DB", "빅데이터", "전산", "백엔드", "프론트엔드"]:
            if token in q:
                slots["관심분야"] = token
                break
    # "직무 자격증"만 있고 직무/전공 미추출 시: 관심분야 fallback (시스템 운영 직무 자격증 등)
    if not slots["관심분야"] and "직무" in q and "자격증" in q:
        slots["관심분야"] = "정보처리 IT 자격증"

    if "다음으로" in q or "뭘 따면" in q or ("다음" in q and "자격증" in q):
        slots["원하는_결과"] = "다음 단계 자격증 추천"
    elif "땄는데" in q:
        slots["원하는_결과"] = "다음 단계 자격증 추천"
    elif "도전" in q:
        slots["원하는_결과"] = "도전할 만한 자격증 추천"
    elif "준비할 만한" in q:
        slots["원하는_결과"] = "준비할 만한 자격증 추천"
    else:
        slots["원하는_결과"] = "적합한 자격증 추천" if "추천" in q or "뭐가" in q or ("직무" in q and "자격증" in q) else ""

    return slots


# Rewrite 결과를 항상 일정한 5줄 포맷으로 고정해 semantic space 일관성 확보 (2차 고도화).
DENSE_REWRITE_FIXED_KEYS = ["전공", "희망직무", "목적", "관심역량", "추천받고 싶은 자격증 유형"]


def _slots_to_structured_text(
    slots: Dict[str, str],
    original: str,
    profile: Optional[UserProfile] = None,
) -> str:
    """
    슬롯을 dense 문서와 대응되는 구조화 문자열로 변환.
    항상 고정 5줄 포맷(전공/희망직무/목적/관심역량/추천받고 싶은 자격증 유형)을 먼저 출력한 뒤,
    profile이 있으면 학년/관심 자격증/취득 여부를 추가한다.
    """
    # 1) 고정 5줄: 값이 없어도 라벨은 항상 출력해 semantic space 일관성 유지
    major = (slots.get("전공") or "").strip() or (profile.get("major") if profile else "") or ""
    job = (slots.get("희망직무") or "").strip()
    purpose = (slots.get("목적") or "").strip()
    interest = (slots.get("관심분야") or "").strip()
    want_type = (slots.get("원하는_결과") or "").strip() or ("적합한 자격증 추천" if "추천" in (original or "") or "뭐가" in (original or "") else "")

    lines = [
        "전공: " + major,
        "희망직무: " + job,
        "목적: " + purpose,
        "관심역량: " + interest,
        "추천받고 싶은 자격증 유형: " + want_type,
    ]
    # "다음 단계" / "미리 준비" 질의: 벡터 매칭을 위해 자격증 키워드 노출
    if want_type and ("다음" in want_type or "준비" in want_type):
        lines.append("관련 자격증: 정보처리기사 SQLD ADsP 컴퓨터활용능력 로드맵")
    # 추천/직무/자격증 질의 전반: 청크와의 어휘 겹침 확대 (contrastive 전까지)
    if any(kw in (original or "") for kw in ["추천", "뭐가", "다음", "준비", "직무", "자격증", "따면", "가려면", "가고", "땄는데", "분석가", "있어"]):
        lines.append("키워드: 정보처리기사 SQLD ADsP 빅데이터분석기사 자격증")
    # 다른 방식: 짧은 쿼리(5단어 이하) 시 보조 키워드 라인 추가 (키워드 라인 없을 때만)
    _orig_tokens = (original or "").strip().split()
    _short_threshold = 5
    if len(_orig_tokens) <= _short_threshold and not any("키워드" in ln for ln in lines):
        try:
            from app.rag.config import get_rag_settings
            if get_rag_settings().RAG_DENSE_SHORT_QUERY_BOOST:
                lines.append("보조 키워드: 정보처리 SQLD ADsP 자격증 취업")
        except Exception:
            pass
    # 다른 방식 확장: 6~9단어 중간 길이일 때 보조 라인 한 줄 (키워드 라인 없을 때만, 기본 OFF)
    if 6 <= len(_orig_tokens) <= 9 and not any("키워드" in ln for ln in lines):
        try:
            from app.rag.config import get_rag_settings
            if get_rag_settings().RAG_DENSE_MEDIUM_QUERY_BOOST:
                lines.append("보조 키워드: 직무 로드맵 추천 정보처리")
        except Exception:
            pass
    # 2) 학년: 슬롯에서 추출한 "N학년" 또는 profile
    grade_from_slot = (slots.get("학년") or "").strip()
    if grade_from_slot:
        lines.append(f"학년: {grade_from_slot}")
    elif profile and profile.get("grade_level") is not None:
        try:
            g = int(profile["grade_level"])
            if 1 <= g <= 4:
                lines.append(f"학년: {g}학년")
        except (TypeError, ValueError):
            pass
    if profile and profile.get("favorite_cert_names"):
        names = profile["favorite_cert_names"][:5]
        if names:
            lines.append(f"관심 자격증: {', '.join(names)}")
    if profile and profile.get("acquired_cert_names"):
        acq_names = profile["acquired_cert_names"][:10]
        if acq_names:
            lines.append(f"취득 자격증: {', '.join(acq_names)}")
    elif profile and profile.get("acquired_qual_ids"):
        lines.append("이미 취득 자격증 있음")

    text = "\n".join(lines)
    orig = (original or "").strip()
    # fallback: 슬롯이 거의 비었을 때 원문 핵심 구를 넣어 vector 매칭 기회 확대 (neither/vec_only 대응)
    if orig and orig not in text:
        if not any([major, job, purpose, interest]) and not want_type:
            text += f"\n원문: {orig[:120]}"
        else:
            text += f"\n원문: {orig}"
    return text.strip()


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
    slots = _extract_slots(q)
    return _slots_to_structured_text(slots, q, profile=profile)


def extract_slots_for_dense(query: str) -> Dict[str, Any]:
    """다른 모듈에서 슬롯만 필요할 때 (예: metadata soft scoring)."""
    return _extract_slots(query or "")
