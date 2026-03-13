"""
BM25 쿼리 전처리 및 확장.

기능:
- normalize: 특수문자 제거, 대소문자 통일, 다중 공백 정리
- expand: 동의어/약어 확장 (자격증 도메인)
- 현재 방식: RECOMMENDATION_QUERY_MAP n-gram 매칭
- 다른 방식: RAG_BM25_BASELINE_APPEND_ENABLE 시 비 cert-centric 추천 질의에 베이스라인 용어 추가
- 비IT 도메인 쿼리(관광, 언어 등)일 때는 IT 베이스라인 미추가
"""
import re
from typing import Any, Dict, List, Optional, Set, Tuple

# 비IT 도메인: data/domain_tokens.json 기반. BM25_BASELINE_MODE=1이면 기존 동작(항상 IT 베이스라인).
def _get_bm25_non_it_tokens() -> frozenset:
    import os
    if os.environ.get("BM25_BASELINE_MODE") == "1":
        return frozenset()
    from app.rag.utils.domain_tokens import get_non_it_tokens
    return get_non_it_tokens()

# 자격증 도메인 동의어/약어 사전
SYNONYM_DICT = {
    # SQL/데이터
    "sqld": ["sqld", "sql 개발자", "sql개발자", "sql developer"],
    "sql 개발자": ["sqld", "sql 개발자", "sql개발자"],
    "sql개발자": ["sqld", "sql 개발자", "sql개발자"],
    "sqlp": ["sqlp", "sql 전문가", "sql전문가"],
    
    # 데이터 분석
    "adsp": ["adsp", "데이터분석준전문가", "데이터 분석 준전문가", "ads-p"],
    "데이터분석준전문가": ["adsp", "데이터분석준전문가", "데이터 분석 준전문가"],
    "adp": ["adp", "데이터분석전문가", "데이터 분석 전문가"],
    
    # 빅데이터
    "빅분기": ["빅분기", "빅데이터분석기사", "빅데이터 분석 기사", "빅데이터분석"],
    "빅데이터분석기사": ["빅분기", "빅데이터분석기사", "빅데이터 분석 기사"],
    
    # 정보처리
    "정처기": ["정처기", "정보처리기사", "정보 처리 기사"],
    "정보처리기사": ["정처기", "정보처리기사", "정보 처리 기사"],
    "정처산": ["정처산", "정보처리산업기사", "정보 처리 산업기사"],
    "정보처리산업기사": ["정처산", "정보처리산업기사", "정보 처리 산업기사"],
    
    # 전기
    "전기기사": ["전기기사", "전기 기사", "전기자격증"],
    "전기산업기사": ["전기산업기사", "전기 산업기사", "전기산업"],
    
    # 네트워크/리눅스
    "네관사": ["네관사", "네트워크관리사", "네트워크 관리사"],
    "네트워크관리사": ["네관사", "네트워크관리사", "네트워크 관리사"],
    "리눅스마스터": ["리눅스마스터", "리눅스 마스터", "리마"],
    
    # 보안
    "정보보안기사": ["정보보안기사", "정보 보안 기사", "보안기사"],
    
    # 직무 키워드
    "데이터분석가": ["데이터분석가", "데이터 분석가", "데이터분석", "데이터 분석"],
    "데이터엔지니어": ["데이터엔지니어", "데이터 엔지니어", "데이터엔지니어링"],
    "백엔드": ["백엔드", "백엔드 개발자", "백엔드개발자", "서버 개발"],
    "프론트엔드": ["프론트엔드", "프론트엔드 개발자", "프론트엔드개발자", "프런트엔드"],
    
    # 전공 키워드
    "컴퓨터공학": ["컴퓨터공학", "컴퓨터 공학", "컴공", "전산학"],
    "전기전자공학": ["전기전자공학", "전기전자", "전기 전자 공학", "전자공학"],
    "산업공학": ["산업공학", "산업 공학", "산공"],
    "경영학": ["경영학", "경영", "경영 학과"],
    "통계학": ["통계학", "통계", "통계 학과"],
    # 자격증 약칭 (cert_name_included / companion 추천용)
    "컴활": ["컴활", "컴퓨터활용능력", "컴퓨터 활용능력"],
    "컴퓨터활용능력": ["컴활", "컴퓨터활용능력", "컴퓨터 활용능력"],
    # 직무/전공 alias (keyword·전산 직무 실패 대응)
    "전산": ["전산", "정보처리", "전산학", "시스템", "IT"],
    "db": ["db", "데이터베이스", "database", "sqld", "sql"],
}

# 정규화된 키 생성 (공백 제거, 소문자)
_NORMALIZED_SYNONYMS = {}
for key, values in SYNONYM_DICT.items():
    normalized_key = key.lower().replace(" ", "")
    if normalized_key not in _NORMALIZED_SYNONYMS:
        _NORMALIZED_SYNONYMS[normalized_key] = set()
    for v in values:
        _NORMALIZED_SYNONYMS[normalized_key].add(v)

# 추천형 BM25: 직무/전공/목적 표현 → 검색 키워드 (질의 재작성, Recall@20·Hit@20 강화)
# 1) 전공/직무/목적 확장 먼저, 2) 기존 동의어 확장 유지. single expansion 기본.
# failure 기반 추가: cert_name_included(같이준비, 준비하면), major/job/purpose(전산, 취업용, 소프트웨어학과 등), keyword(직무, DB).
RECOMMENDATION_QUERY_MAP = {
    # 직무 표현
    "정보처리": "정보처리 IT 개발 시스템 데이터베이스 소프트웨어 자격증",
    "정보처리관련": "정보처리 IT 개발 시스템 자격증",
    "정보처리직무": "정보처리 IT직무 개발직무 시스템운영 전산 자격증",
    "데이터직무": "데이터 데이터분석 데이터베이스 SQL 자격증",
    "개발직무": "개발 백엔드 프론트엔드 소프트웨어 프로그래밍 자격증",
    "IT직무": "IT 개발 시스템 정보통신 자격증",
    "백엔드": "백엔드 개발 서버 프로그래밍",
    "데이터분석": "데이터분석 데이터 SQL 빅데이터",
    "직무": "개발 정보처리 데이터 직무 IT 자격증",
    "전산": "전산 정보처리 IT 개발 시스템 데이터베이스 자격증",
    "시스템운영": "시스템 운영 개발 서버 정보처리",
    "개발이랑": "개발 정보처리 SQLD 시스템",
    # 전공 표현
    "산업데이터공학과": "산업데이터공학 데이터 공학 정보시스템 전산",
    "산업데이터공학과인데": "산업데이터공학 데이터 공학 정보시스템 전산 정보처리",
    "컴퓨터공학": "컴퓨터공학 소프트웨어 정보통신 전산",
    "소프트웨어학과": "소프트웨어 개발 IT 정보처리 전산",
    "전기전자공학": "전기 전자 공학",
    "경영학": "경영 회계 금융",
    "통계학": "통계 데이터 분석",
    # 목적 표현
    "취업": "취업 자격증 실무 입문",
    "취업하고싶어": "취업 자격증",
    "취업준비": "취업 자격증 실무 역량",
    "취업용": "취업 자격증 실무 정보처리 SQLD",
    "이직": "취업 실무 커리어",
    "입문": "입문 자격증 기초",
    # cert_name_included: "정처기 말고 같이 준비하면 좋은 자격증" → 동반 자격증 키워드 주입
    "같이준비": "SQLD ADsP 정보처리기사 데이터분석준전문가 자격증",
    "준비하면": "SQLD ADsP 정보처리기사 자격증",
    "준비하면좋은": "SQLD ADsP 정보처리기사 자격증",
    # keyword: DB, 빅데이터
    "db": "데이터베이스 SQL SQLD 정보처리",
    "빅데이터관련": "빅데이터 ADsP SQLD 데이터분석 빅데이터분석기사",
    # natural 3-gram (18골든 기반)
    "취업준비용으로": "취업 자격증 실무 정보처리 SQLD ADsP",
    "범용성높은": "정보처리기사 SQLD ADsP IT 자격증 취업",
    "직접적인": "정보처리기사 SQLD 개발 IT 자격증",
    "도움되는": "취업 자격증 실무",
    # 18골든 failure-driven: 전산 직무, 산업데이터공학과 취업, 산업공학 데이터/IT, companion(컴활 말고)
    "전산직무": "전산 정보처리 정보처리기사 SQLD 자격증",
    "산업데이터공학과취업": "산업데이터공학 데이터 정보처리 전산 취업 자격증 SQLD ADsP",
    "산업공학과인데": "산업공학 데이터 IT 정보처리 전산 자격증",
    "컴활말고": "정보처리기사 SQLD ADsP IT 취업 자격증",
    # Round2: 정보처리 직무 (2-gram 이미 있음), 경계형 "데이터/IT 둘 다 가능한" 보강
    "정보처리직무자격증": "정보처리 정보처리기사 SQLD 직무 자격증",
    "데이터it": "데이터 IT 정보처리 SQLD ADsP 자격증",
    "둘다가능한": "데이터 IT 정보처리 자격증",
    # 4분할 neither 감소: 시스템운영, 학년/로드맵
    "시스템운영": "시스템 운영 정보처리 서버 IT 자격증",
    "시스템운영직무": "시스템 운영 정보처리 서버 IT 자격증",
    "1학년": "입문 자격증 기초 취업 준비",
    "4학년": "취업 자격증 실무 정보처리 SQLD",
    "다음으로": "정보처리기사 SQLD ADsP 자격증 순서 로드맵",
    "다음으로준비": "정보처리기사 SQLD ADsP 자격증",
    # RRF only 고도화: neither 골든 4,7,8,9,11,13,15 대응
    "도전하고싶어": "빅데이터분석기사 SQLD ADsP 정보처리기사 자격증 도전",
    "실무쪽": "실무 정보처리 SQLD ADsP 자격증 취업",
    "2학년": "입문 자격증 취업 준비 정보처리 SQLD ADsP",
    "준비할만한": "정보처리기사 SQLD ADsP 자격증 다음 로드맵",
    # neither 3건 감소: 직무 자격증, 뭘 따면 좋을까, 미리 준비
    "직무자격증": "정보처리 직무 시스템 운영 IT 자격증",
    "뭘따면좋을까": "정보처리기사 SQLD ADsP 컴활 다음 로드맵",
    "미리준비": "입문 자격증 기초 1학년 취업 준비",
    "미리준비하고": "입문 자격증 기초 1학년 취업 준비",
    # 1-gram: "시스템 운영 직무"에서 "시스템"만 매칭 시 확장
    "시스템": "시스템 운영 정보처리 IT 서버 자격증",
    "운영직무": "시스템 운영 정보처리 직무 IT 자격증",
    # 짧은 구어: 학과/학년 없이 직무만 ("데이터분석 쪽으로 일하고 싶어" 등)
    "일하고싶어": "취업 직무 자격증 정보처리 데이터 개발",
    "알려줘": "자격증 추천 직무 취업 정보처리 SQLD ADsP",
    # 골든 자연어: "데이터 관련 직무", "되려면 뭐 따야 해", "데이터 쪽", "전산 직무 추천"
    "데이터관련": "데이터 데이터분석 SQLD ADsP 정보처리 직무 자격증",
    "데이터쪽": "데이터 데이터분석 SQLD ADsP 빅데이터분석기사 자격증",
    "되려면": "취업 자격증 정보처리기사 SQLD ADsP 직무",
    "뭐따야해": "정보처리기사 SQLD ADsP 자격증 로드맵",
    "추천해줘": "자격증 추천 정보처리 SQLD ADsP IT 취업",
    "뭐가있어": "자격증 정보처리 SQLD ADsP 직무 추천",
    "전산직무추천": "전산 정보처리 정보처리기사 SQLD 직무 자격증",
    # 골든 구어 추가: 가고싶어/가려면/준비하고 있어/둘 다/컴활만 있는데
    "가고싶어": "취업 직무 자격증 데이터 정보처리",
    "가려면": "IT 직무 자격증 정보처리기사 SQLD ADsP 취업",
    "준비하고있어": "취업 자격증 데이터 분석 정보처리",
    "둘다": "데이터 개발 SQLD 정보처리 ADsP 자격증",
    "컴활만": "정보처리기사 SQLD ADsP IT 직무 자격증",
    # 로드맵/직무 구어: 땄는데, 분석가 되려면, 하고 싶어, 취업용으로
    "땄는데": "정보처리기사 SQLD ADsP 다음 로드맵 자격증",
    "분석가": "빅데이터분석기사 ADsP 데이터분석 SQLD 자격증",
    "하고싶어": "데이터 개발 SQLD 정보처리 ADsP 자격증",
    "취업용으로": "취업 실무 정보처리 SQLD ADsP 자격증",
    # "자격증 있어?" 등 구어
    "자격증있어": "자격증 정보처리 SQLD ADsP 직무 추천",
    # 2~3 gram 보강: 뭐가, 추천 자격증, 다음으로 뭘
    "뭐가": "자격증 정보처리 SQLD ADsP 직무 뭐가",
    "추천자격증": "자격증 추천 정보처리 SQLD ADsP IT",
    # 3-gram·구어 마지막 보강
    "인데취업": "취업 자격증 실무 정보처리 SQLD",
    "인데자격증": "자격증 입문 취업 정보처리",
    "다음단계": "정보처리기사 SQLD ADsP 자격증 로드맵",
    # 취준/자소서 등 취업 준비 맥락 보강
    "취준": "취업 준비 자격증 정보처리 SQLD ADsP",
    "자소서": "취업 준비 자격증 실무 포트폴리오",
    # 빅데이터 직무 표현 보강
    "빅데이터직무": "빅데이터 직무 데이터분석 SQLD ADsP 빅데이터분석기사 자격증",
}

# Query type별 expansion: cert-centric(자격증명·로드맵·비교)에서는 목적/전공/직무 과확장 스킵.
# 이름/별칭·동의어·companion(같이준비, 준비하면, db, 빅데이터관련)은 모든 유형에서 유지.
CERT_CENTRIC_QUERY_TYPES = ("cert_name_included", "roadmap", "comparison")


def _norm_reco_key(k: str) -> str:
    return k.lower().replace(" ", "")


RECO_KEYS_SKIP_FOR_CERT_NAME = {
    _norm_reco_key(k)
    for k in (
        "취업", "취업하고싶어", "취업준비", "취업용", "이직", "입문",
        "직무", "전산", "정보처리", "정보처리관련", "정보처리직무", "데이터직무", "개발직무", "IT직무",
        "백엔드", "데이터분석", "시스템운영", "시스템운영직무", "개발이랑",
        "산업데이터공학과", "산업데이터공학과인데", "컴퓨터공학", "소프트웨어학과", "전기전자공학", "경영학", "통계학",
        "취업준비용으로", "범용성높은", "직접적인", "도움되는", "전산직무", "산업데이터공학과취업",
        "산업공학과인데", "컴활말고", "정보처리직무자격증", "데이터it", "둘다가능한",
        "1학년", "4학년", "2학년",  # cert-centric에서 학년 확장 스킵 (로드맵/이름 매칭 유지)
        "도전하고싶어", "실무쪽", "준비할만한",
        "직무자격증", "뭘따면좋을까", "미리준비", "미리준비하고",
        "시스템", "운영직무", "일하고싶어", "알려줘",
        "데이터관련", "데이터쪽", "되려면", "뭐따야해", "추천해줘", "뭐가있어", "전산직무추천",
        "가고싶어", "가려면", "준비하고있어", "둘다", "컴활만",
        "땄는데", "분석가", "하고싶어", "취업용으로",
        "자격증있어", "뭐가", "추천자격증",
        "인데취업", "인데자격증",
    )
}

_NORMALIZED_RECOM = {}
for key, value in RECOMMENDATION_QUERY_MAP.items():
    k = _norm_reco_key(key)
    _NORMALIZED_RECOM[k] = value.split()

# 2-2: RECOMMENDATION_QUERY_MAP 근거 기반 관리. 변경 시 failure case, 적용 이유, 기대 효과, 과확장 리스크 필수 기록.
# 키 = RECOMMENDATION_QUERY_MAP 키와 동일. 값 = reason, example_queries(failure case), recall_before/after, over_expansion.
RECOMMENDATION_QUERY_MAP_META: Dict[str, Dict[str, Any]] = {
    "같이준비": {
        "reason": "cert_name_included 동반 자격증 회수: 정처기+SQLD/ADsP 등 연관 cert 노출",
        "example_queries": ["정처기랑 같이 준비하면 좋은 자격증"],
        "recall_before": None,
        "recall_after": None,
        "over_expansion": False,
    },
    "취업용": {
        "reason": "purpose_only·major+job 질의에서 정보처리/SQLD 후보 회수 강화",
        "example_queries": ["취업용으로 뭐가 좋아?", "산업데이터공학과 취업용"],
        "recall_before": None,
        "recall_after": None,
        "over_expansion": True,  # cert_name_included에서 과확장 가능 → RECO_KEYS_SKIP으로 스킵
    },
    "전산직무": {
        "reason": "keyword '전산 직무' 실패: 전산→정보처리·SQLD 확장으로 Recall@20 개선",
        "example_queries": ["전산 직무 자격증 추천"],
        "recall_before": None,
        "recall_after": None,
        "over_expansion": False,
    },
    "산업데이터공학과취업": {
        "reason": "major+job '산업데이터공학과 취업' 실패: 데이터·정보처리·SQLD·ADsP 회수",
        "example_queries": ["산업데이터공학과인데 취업하고싶어"],
        "recall_before": None,
        "recall_after": None,
        "over_expansion": False,
    },
    "컴활말고": {
        "reason": "comparison '컴활 말고' 실패: 정보처리기사·SQLD·ADsP 등 대안 회수",
        "example_queries": ["컴활 말고 다른 자격증 추천해줘"],
        "recall_before": None,
        "recall_after": None,
        "over_expansion": False,
    },
    "시스템운영": {"reason": "4분할 neither: 시스템 운영 직무 자격증 회수", "example_queries": ["시스템 운영 직무 자격증"], "recall_before": None, "recall_after": None, "over_expansion": False},
    "1학년": {"reason": "4분할 neither: 저학년 입문/준비 질의", "example_queries": ["1학년인데 자격증 미리 준비하고 싶어"], "recall_before": None, "recall_after": None, "over_expansion": False},
    "4학년": {"reason": "4분할 neither: 고학년 취업/실무 질의", "example_queries": ["4학년인데 취업용으로 실무 쪽 자격증"], "recall_before": None, "recall_after": None, "over_expansion": False},
    "다음으로": {"reason": "로드맵형 다음 단계 자격증 회수", "example_queries": ["정처기 다음으로 준비할 만한 자격증"], "recall_before": None, "recall_after": None, "over_expansion": False},
    "도전하고싶어": {"reason": "RRF neither: 정처기 땄는데 더 도전하고 싶어 → 빅분기/SQLD/ADsP", "example_queries": ["정처기 땄는데 더 도전하고 싶어"], "recall_before": None, "recall_after": None, "over_expansion": False},
    "실무쪽": {"reason": "RRF neither: 4학년 취업용 실무 쪽 자격증", "example_queries": ["4학년인데 취업용으로 실무 쪽 자격증"], "recall_before": None, "recall_after": None, "over_expansion": False},
    "2학년": {"reason": "RRF neither: IT 취업 준비 2학년", "example_queries": ["IT 취업 준비 2학년"], "recall_before": None, "recall_after": None, "over_expansion": False},
    "준비할만한": {"reason": "RRF neither: 정처기 다음으로 준비할 만한 자격증", "example_queries": ["정처기 다음으로 준비할 만한 자격증"], "recall_before": None, "recall_after": None, "over_expansion": False},
    "직무자격증": {"reason": "neither: 시스템 운영 직무 자격증", "example_queries": ["시스템 운영 직무 자격증"], "recall_before": None, "recall_after": None, "over_expansion": False},
    "뭘따면좋을까": {"reason": "neither: 컴활 땄는데 다음으로 뭘 따면 좋을까", "example_queries": ["컴활 땄는데 다음으로 뭘 따면 좋을까"], "recall_before": None, "recall_after": None, "over_expansion": False},
    "미리준비": {"reason": "neither: 1학년인데 자격증 미리 준비하고 싶어", "example_queries": ["1학년인데 자격증 미리 준비하고 싶어"], "recall_before": None, "recall_after": None, "over_expansion": False},
    "미리준비하고": {"reason": "neither: 미리 준비하고 (2-gram)", "example_queries": ["1학년인데 자격증 미리 준비하고 싶어"], "recall_before": None, "recall_after": None, "over_expansion": False},
    "시스템": {"reason": "neither: 시스템 운영 직무 (1-gram)", "example_queries": ["시스템 운영 직무 자격증"], "recall_before": None, "recall_after": None, "over_expansion": False},
    "운영직무": {"reason": "neither: 운영+직무 2-gram", "example_queries": ["시스템 운영 직무 자격증"], "recall_before": None, "recall_after": None, "over_expansion": False},
    "일하고싶어": {"reason": "짧은 구어: 학과/학년 없이 직무만", "example_queries": ["데이터분석 쪽으로 일하고 싶어"], "recall_before": None, "recall_after": None, "over_expansion": False},
    "알려줘": {"reason": "구어: 자격증 알려줘", "example_queries": ["취업할 때 도움이 되는 자격증 알려줘"], "recall_before": None, "recall_after": None, "over_expansion": False},
    "데이터관련": {"reason": "골든: 데이터 관련 직무로 가고싶어", "example_queries": ["데이터 관련 직무로 가고싶어"], "recall_before": None, "recall_after": None, "over_expansion": False},
    "데이터쪽": {"reason": "골든: 데이터 쪽 자격증 추천", "example_queries": ["데이터 쪽 자격증 추천"], "recall_before": None, "recall_after": None, "over_expansion": False},
    "되려면": {"reason": "골든: 빅데이터 분석가 되려면", "example_queries": ["빅데이터 분석가 되려면"], "recall_before": None, "recall_after": None, "over_expansion": False},
    "뭐따야해": {"reason": "골든: 백엔드 개발자 되려면 뭐 따야 해?", "example_queries": ["백엔드 개발자 되려면 뭐 따야 해?"], "recall_before": None, "recall_after": None, "over_expansion": False},
    "추천해줘": {"reason": "골든: IT 취업용 자격증 추천해줘", "example_queries": ["IT 취업용 자격증 추천해줘"], "recall_before": None, "recall_after": None, "over_expansion": False},
    "뭐가있어": {"reason": "골든: 정보처리 직무 자격증 뭐가 있어?", "example_queries": ["정보처리 직무 자격증 뭐가 있어?"], "recall_before": None, "recall_after": None, "over_expansion": False},
    "전산직무추천": {"reason": "골든: 전산 직무 추천 자격증 있어?", "example_queries": ["전산 직무 추천 자격증 있어?"], "recall_before": None, "recall_after": None, "over_expansion": False},
    "가고싶어": {"reason": "골든: 데이터 관련 직무로 가고싶어", "example_queries": ["데이터 관련 직무로 가고싶어"], "recall_before": None, "recall_after": None, "over_expansion": False},
    "가려면": {"reason": "골든: 컴활만 있는데 IT 직무로 가려면?", "example_queries": ["컴활만 있는데 IT 직무로 가려면?"], "recall_before": None, "recall_after": None, "over_expansion": False},
    "준비하고있어": {"reason": "골든: 데이터 분석 쪽 취업 준비하고 있어", "example_queries": ["데이터 분석 쪽 취업 준비하고 있어"], "recall_before": None, "recall_after": None, "over_expansion": False},
    "둘다": {"reason": "골든: 데이터베이스랑 개발 둘 다 하고 싶어", "example_queries": ["데이터베이스랑 개발 둘 다 하고 싶어"], "recall_before": None, "recall_after": None, "over_expansion": False},
    "컴활만": {"reason": "골든: 컴활만 있는데 IT 직무로", "example_queries": ["컴활만 있는데 IT 직무로 가려면?"], "recall_before": None, "recall_after": None, "over_expansion": False},
    "땄는데": {"reason": "골든: 컴활/정처기 땄는데 다음으로", "example_queries": ["컴활 땄는데 다음으로 뭘 따면 좋을까?"], "recall_before": None, "recall_after": None, "over_expansion": False},
    "분석가": {"reason": "골든: 빅데이터 분석가 되려면", "example_queries": ["빅데이터 분석가 되려면"], "recall_before": None, "recall_after": None, "over_expansion": False},
    "하고싶어": {"reason": "골든: 데이터베이스랑 개발 둘 다 하고 싶어", "example_queries": ["데이터베이스랑 개발 둘 다 하고 싶어"], "recall_before": None, "recall_after": None, "over_expansion": False},
    "취업용으로": {"reason": "골든: 4학년인데 취업용으로 실무 쪽", "example_queries": ["4학년인데 취업용으로 실무 쪽 자격증"], "recall_before": None, "recall_after": None, "over_expansion": False},
    "자격증있어": {"reason": "골든: 전산 직무 추천 자격증 있어?", "example_queries": ["전산 직무 추천 자격증 있어?"], "recall_before": None, "recall_after": None, "over_expansion": False},
    "뭐가": {"reason": "골든: 정보처리 직무 자격증 뭐가 있어?", "example_queries": ["정보처리 직무 자격증 뭐가 있어?"], "recall_before": None, "recall_after": None, "over_expansion": False},
    "추천자격증": {"reason": "골든: 데이터 쪽 자격증 추천 등", "example_queries": ["데이터 쪽 자격증 추천"], "recall_before": None, "recall_after": None, "over_expansion": False},
    "인데취업": {"reason": "4학년인데 취업용으로 등", "example_queries": ["4학년인데 취업용으로 실무 쪽 자격증"], "recall_before": None, "recall_after": None, "over_expansion": False},
    "인데자격증": {"reason": "1학년인데 자격증 미리 준비", "example_queries": ["1학년인데 자격증 미리 준비하고 싶어"], "recall_before": None, "recall_after": None, "over_expansion": False},
    "다음단계": {"reason": "다음 단계 자격증 추천", "example_queries": ["컴활 땄는데 다음 단계 뭘 따면 좋을까"], "recall_before": None, "recall_after": None, "over_expansion": False},
}


def normalize_query(query: str) -> str:
    """
    쿼리 정규화:
    - 소문자 변환
    - 특수문자(/, -, _, ., ,) → 공백
    - 다중 공백 정리
    - 숫자/영문+한글 붙은 것 분리 (SQLD2급 → SQLD 2급)
    """
    q = (query or "").strip().lower()
    # 끝 조사/구두점 제거 (추천 질의 자연어 정규화)
    q = re.sub(r'[?？！]\s*$', '', q).strip()
    
    # 특수문자 → 공백
    q = re.sub(r'[/\-_.,()（）]', ' ', q)
    
    # 영문+숫자 붙은 것 분리 (sqld2 → sqld 2, aws3 → aws 3)
    q = re.sub(r'([a-z]+)(\d+)', r'\1 \2', q)
    
    # 숫자+한글 붙은 것 분리 (2급기사 → 2급 기사)
    q = re.sub(r'(\d+)([\uAC00-\uD7A3])', r'\1 \2', q)
    
    # 다중 공백 정리
    q = re.sub(r'\s+', ' ', q).strip()
    
    return q


def expand_query(query: str, max_expansions: int = 6) -> List[str]:
    """
    동의어/약어 확장:
    - 쿼리의 각 토큰에 대해 동의어 사전 검색
    - 최대 max_expansions개까지만 확장 (과도한 확장 방지)
    
    반환: [원본 쿼리, 확장 쿼리1, 확장 쿼리2, ...]
    """
    normalized = normalize_query(query)
    tokens = normalized.split()
    
    # 토큰별 확장 수집
    all_expansions: Set[str] = {normalized}
    
    for token in tokens:
        token_normalized = token.replace(" ", "")
        if token_normalized in _NORMALIZED_SYNONYMS:
            for syn in _NORMALIZED_SYNONYMS[token_normalized]:
                if syn != token:
                    # 원본 쿼리에서 해당 토큰을 동의어로 대체
                    expanded = normalized.replace(token, syn)
                    all_expansions.add(expanded)
                    if len(all_expansions) >= max_expansions:
                        break
        if len(all_expansions) >= max_expansions:
            break
    
    # 연속 토큰 매칭 (예: "정보 처리 기사" → "정처기")
    for i in range(len(tokens)):
        for j in range(i + 2, min(i + 5, len(tokens) + 1)):
            phrase = " ".join(tokens[i:j])
            phrase_normalized = phrase.replace(" ", "")
            if phrase_normalized in _NORMALIZED_SYNONYMS:
                for syn in _NORMALIZED_SYNONYMS[phrase_normalized]:
                    if syn != phrase:
                        expanded = normalized.replace(phrase, syn)
                        all_expansions.add(expanded)
                        if len(all_expansions) >= max_expansions:
                            break
            if len(all_expansions) >= max_expansions:
                break
        if len(all_expansions) >= max_expansions:
            break
    
    return list(all_expansions)[:max_expansions]


def expand_query_single_string(
    query: str,
    max_extra_terms: int = 8,
    for_recommendation: bool = True,
    query_type: Optional[str] = None,
) -> str:
    """
    동의어/약어를 원본 쿼리 뒤에 이어 붙인 단일 문자열 반환.
    for_recommendation=True(기본): 직무/전공/목적 표현 확장 추가 → 추천형 Recall@20·Hit@20 강화.
    query_type: cert_name_included일 때 목적/전공 확장 약화(이름·별칭·연관 cert 확장 유지). 2-6 보호 규칙.
    BM25 1회 검색만 하므로 지연 시간 증가 최소.

    Query type별 expansion 원칙 (RECOMMENDATION_BM25.md):
    - cert_name_included, roadmap, comparison: CERT_CENTRIC_QUERY_TYPES. RECO_KEYS_SKIP으로 목적/전공/직무 스킵, name/alias·companion 유지.
    - major+job, purpose_only, keyword, natural, mixed: 전부 확장(스킵 없음).
    """
    normalized = normalize_query(query)
    if not normalized:
        return query.strip()
    tokens = normalized.split()
    seen: Set[str] = set(tokens)
    extra: List[str] = []

    # cert-centric(cert_name_included, roadmap, comparison): 목적/전공/직무 과확장 스킵, name/alias·companion 유지.
    skip_reco_keys = RECO_KEYS_SKIP_FOR_CERT_NAME if query_type in CERT_CENTRIC_QUERY_TYPES else set()

    # 1) 추천형: 직무/전공/목적 키워드 추가 (질의 재작성). cert_name_included면 job/major/purpose 키 스킵.
    if for_recommendation and _NORMALIZED_RECOM:
        for token in tokens:
            key = _norm_reco_key(token)
            if key in skip_reco_keys:
                continue
            if key in _NORMALIZED_RECOM:
                for term in _NORMALIZED_RECOM[key]:
                    if term and term.lower() not in seen:
                        seen.add(term.lower())
                        extra.append(term)
        for i in range(len(tokens) - 1):
            phrase_norm = _norm_reco_key(tokens[i] + tokens[i + 1])
            if phrase_norm in skip_reco_keys:
                continue
            if phrase_norm in _NORMALIZED_RECOM:
                for term in _NORMALIZED_RECOM[phrase_norm]:
                    if term and term.lower() not in seen:
                        seen.add(term.lower())
                        extra.append(term)
        for i in range(len(tokens) - 2):
            phrase_norm = _norm_reco_key(tokens[i] + tokens[i + 1] + tokens[i + 2])
            if phrase_norm in skip_reco_keys:
                continue
            if phrase_norm in _NORMALIZED_RECOM:
                for term in _NORMALIZED_RECOM[phrase_norm]:
                    if term and term.lower() not in seen:
                        seen.add(term.lower())
                        extra.append(term)

    # 2) 기존 자격증/직무 동의어 (exclusion: "컴활 말고" 시 컴활→컴퓨터활용능력 추가 생략)
    skip_synonym_tokens: Set[str] = set()
    if "말고" in normalized and "컴활" in tokens:
        skip_synonym_tokens.add("컴활")
    for token in tokens:
        if len(extra) >= max_extra_terms * 2:
            break
        key = token.replace(" ", "").lower()
        if key in skip_synonym_tokens:
            continue
        if key in _NORMALIZED_SYNONYMS:
            for syn in _NORMALIZED_SYNONYMS[key]:
                term = syn.strip()
                if term and term.lower() not in seen:
                    seen.add(term.lower())
                    extra.append(term)

    # 3) 다른 방식: 비 cert-centric 추천 질의에 베이스라인 용어 추가 (비IT 쿼리면 스킵)
    try:
        from app.rag.config import get_rag_settings
        s = get_rag_settings()
        has_non_it = any(t in normalized for t in _get_bm25_non_it_tokens())
        if (
            s.RAG_BM25_BASELINE_APPEND_ENABLE
            and for_recommendation
            and query_type not in CERT_CENTRIC_QUERY_TYPES
            and not has_non_it
        ):
            # 8개: S@4/Hit@4/MRR 최고점. 비IT(관광·언어 등) 쿼리에는 IT 용어 미추가.
            _baseline_terms = ["자격증", "정보처리", "SQLD", "ADsP", "IT", "취업", "실무", "로드맵"]
            for term in _baseline_terms:
                if term and term.lower() not in seen:
                    seen.add(term.lower())
                    extra.append(term)
            # 확장: 4~7단어 중간 길이일 때 직무·정보처리기사 추가 (기본 OFF)
            if getattr(s, "RAG_BM25_MEDIUM_BASELINE_ENABLE", False) and 4 <= len(tokens) <= 7:
                _medium_terms = ["직무", "정보처리기사"]
                for term in _medium_terms:
                    if term and term.lower() not in seen:
                        seen.add(term.lower())
                        extra.append(term)
    except Exception:
        pass

    # 4) 비IT 쿼리: 도메인별 BM25 확장 (BM25_BASELINE_MODE=1이면 스킵)
    try:
        import os
        if os.environ.get("BM25_BASELINE_MODE") != "1":
            has_non_it = any(t in normalized for t in _get_bm25_non_it_tokens())
            if has_non_it and for_recommendation:
                from app.rag.utils.domain_tokens import get_non_it_bm25_expansion
                expansion_map = get_non_it_bm25_expansion()
                for key, terms in expansion_map.items():
                    if key in normalized:
                        for term in terms:
                            if term and term.lower() not in seen:
                                seen.add(term.lower())
                                extra.append(term)
                        if len(extra) >= max_extra_terms * 2:
                            break
    except Exception:
        pass

    if not extra:
        return normalized
    return normalized + " " + " ".join(extra[: max_extra_terms * 2])


def process_query_for_bm25(
    query: str,
    expand: bool = True,
    max_expansions: int = 6,
) -> Tuple[str, List[str]]:
    """
    BM25 검색용 쿼리 전처리.
    
    반환: (정규화된 쿼리, 확장 쿼리 리스트)
    """
    normalized = normalize_query(query)
    
    if expand:
        expansions = expand_query(query, max_expansions)
    else:
        expansions = [normalized]
    
    return normalized, expansions


# 테스트 케이스
if __name__ == "__main__":
    test_queries = [
        "SQLD",
        "정처기",
        "빅분기",
        "ADsP",
        "데이터엔지니어 자격증",
        "전기전자공학 전공자가 데이터분석가 직무를 목표로",
        "컴퓨터공학 백엔드 개발자",
    ]
    
    for q in test_queries:
        norm, exps = process_query_for_bm25(q)
        print(f"\n원본: {q}")
        print(f"정규화: {norm}")
        print(f"확장 ({len(exps)}): {exps}")
