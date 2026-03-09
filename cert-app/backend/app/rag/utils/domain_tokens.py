"""
Supabase 데이터셋 기반 IT/비IT 도메인 토큰.
data/domain_tokens.json이 있으면 로드, 없으면 하드코딩 기본값 사용.
"""
from pathlib import Path
from typing import Any, Dict, List

# 기본값: export_domain_tokens.py 실행 전 또는 JSON 없을 때 사용
_DEFAULT_IT_TOKENS = frozenset({
    "정보처리", "IT", "개발", "데이터", "DB", "SQL", "빅데이터", "백엔드", "프론트엔드",
    "전산", "소프트웨어", "컴퓨터", "시스템", "네트워크", "보안", "클라우드",
    "정보통신", "정보기술개발", "데이터분석", "데이터베이스", "시스템관리", "네트워크관리",
    "정보보안", "산업데이터공학", "시스템운영", "IT서비스",
})
_DEFAULT_NON_IT_TOKENS = frozenset({
    "관광", "언어", "호텔", "여행", "간호", "의료", "회계", "금융", "건설", "기계",
    "조리", "영양", "사회복지", "교육", "스포츠", "미용", "부동산", "물류", "농업",
    "수산", "식품", "경제", "보건", "통역", "번역", "디자인", "예술", "경영", "마케팅",
})
_DEFAULT_NON_IT_BM25_EXPANSION: Dict[str, List[str]] = {
    "관광": ["호텔", "여행", "관광통역", "관광통역안내사", "호텔경영"],
    "언어": ["관광통역", "외국어", "통역", "번역", "관광통역안내사"],
    "간호": ["의료", "보건", "간호사"],
    "의료": ["보건", "간호", "의료기사"],
    "회계": ["금융", "세무", "전산회계"],
    "금융": ["재무", "세무", "금융"],
    "조리": ["영양", "식품", "조리사"],
    "영양": ["식품", "조리", "영양사"],
    "사회복지": ["복지", "상담", "사회복지사"],
    "교육": ["교사", "교육학"],
    "건설": ["건축", "토목", "건설기술"],
    "기계": ["기계", "메카트로닉스", "자동화"],
}

_cached: Dict[str, Any] | None = None


def _domain_tokens_path() -> Path:
    try:
        from app.rag.config import get_rag_index_dir, get_rag_settings
        base = get_rag_index_dir().parent  # data/
    except Exception:
        base = Path("data")
    return base / "domain_tokens.json"


def load_domain_tokens() -> Dict[str, Any]:
    """data/domain_tokens.json 로드. 없으면 기본값 반환."""
    global _cached
    if _cached is not None:
        return _cached
    path = _domain_tokens_path()
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                import json
                data = json.load(f)
            _cached = {
                "it_tokens": frozenset(data.get("it_tokens", []) or list(_DEFAULT_IT_TOKENS)),
                "non_it_tokens": frozenset(data.get("non_it_tokens", []) or list(_DEFAULT_NON_IT_TOKENS)),
                "non_it_bm25_expansion": data.get("non_it_bm25_expansion") or _DEFAULT_NON_IT_BM25_EXPANSION,
            }
            return _cached
        except Exception:
            pass
    _cached = {
        "it_tokens": _DEFAULT_IT_TOKENS,
        "non_it_tokens": _DEFAULT_NON_IT_TOKENS,
        "non_it_bm25_expansion": _DEFAULT_NON_IT_BM25_EXPANSION,
    }
    return _cached


def get_it_tokens() -> frozenset:
    return load_domain_tokens()["it_tokens"]


def get_non_it_tokens() -> frozenset:
    return load_domain_tokens()["non_it_tokens"]


def get_non_it_bm25_expansion() -> Dict[str, List[str]]:
    return load_domain_tokens()["non_it_bm25_expansion"]
