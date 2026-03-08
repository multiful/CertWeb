"""
BM25 전용 개인화 쿼리 재구성.
질문 + 사용자 프로필(전공, 즐겨찾기 분야)을 sparse-friendly하게 합쳐 BM25 검색 품질을 높인다.
이미 취득한 자격증은 query에 넣지 않고 re-ranking에서만 반영.
2차: 직무 목표·전공·favorite 분야·취업/입문/실무 목적을 가볍게 반영, 장황함 방지.
"""
from typing import List, Optional

from app.rag.utils.query_processor import expand_query_single_string
from app.rag.utils.dense_query_rewrite import UserProfile

# 전공 → BM25에 넣을 sparse 토큰 (직무 연관 보강)
MAJOR_TO_SPARSE_TOKENS: dict[str, str] = {
    "산업데이터공학과": "데이터 정보처리 IT 데이터분석 데이터베이스",
    "컴퓨터공학": "개발 정보처리 IT",
    "컴퓨터공학과": "개발 정보처리 IT",
    "소프트웨어학과": "개발 IT 시스템",
    "정보통신": "정보처리 IT",
    "정보통신학과": "정보처리 IT 개발",
    "경영학": "경영 회계",
    "경영학과": "경영 회계",
    "통계학": "데이터 분석",
    "통계학과": "데이터 분석",
    "산업공학": "데이터 IT 정보처리",
    "산업공학과": "데이터 IT 정보처리",
}


def _add_unique(tokens: List[str], seen: set, extra: List[str], cap: int) -> None:
    """seen에 없으면 extra에 추가, cap까지."""
    for t in tokens:
        if len(extra) >= cap:
            return
        w = (t or "").strip()
        if not w:
            continue
        for part in w.replace(",", " ").split():
            part = part.strip()
            if part and part.lower() not in seen:
                seen.add(part.lower())
                extra.append(part)


def build_personalized_bm25_query(
    query: str,
    profile: Optional[UserProfile] = None,
    max_extra_terms: int = 12,
) -> str:
    """
    질문 + 프로필 기반 BM25용 쿼리 문자열.
    - profile 없으면 expand_query_single_string(query) 반환 (기존 동작).
    - profile 있으면: 기존 확장 + 직무/목적 추출어 + 전공 sparse + 즐겨찾기 분야(field/job 토큰).
    - 이미 취득(acquired)은 query에 넣지 않음. rerank에서 반영.
    """
    base = expand_query_single_string(query, for_recommendation=True)
    if not profile:
        return base

    extra: List[str] = []
    seen = set(base.lower().split())

    # 1) 직무/목적은 base의 RECOMMENDATION_QUERY_MAP에서 이미 확장되므로 여기서 중복 확장하지 않음.
    #    (과한 확장이 BM25 term 분산을 일으켜 recall 하락 방지)

    cap_extra = min(max_extra_terms, 8)
    # 2) 전공: 매핑 테이블 우선, 없으면 첫 토큰만
    major = (profile.get("major") or "").strip()
    if major:
        major_norm = major.replace(" ", "").lower()
        matched = False
        for key, tokens in MAJOR_TO_SPARSE_TOKENS.items():
            if key.replace(" ", "").lower() in major_norm or major_norm in key.replace(" ", "").lower():
                _add_unique(tokens.split(), seen, extra, cap_extra)
                matched = True
                break
        if not matched:
            first = major.split()[0] if major.split() else major
            if first and first.lower() not in seen:
                seen.add(first.lower())
                extra.append(first)

    # 3) 즐겨찾기 분야: favorite_field_tokens (main_field/ncs_large 기반), 최대 4개
    favorite_tokens = profile.get("favorite_field_tokens") or []
    for t in favorite_tokens[:4]:
        if not t or not isinstance(t, str):
            continue
        _add_unique([t], seen, extra, cap_extra)

    if not extra:
        return base
    capped = extra[:cap_extra]
    return base + " " + " ".join(capped)
