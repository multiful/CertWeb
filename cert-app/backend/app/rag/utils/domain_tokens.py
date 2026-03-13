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
_broad_domains_cache: Dict[str, List[str]] | None = None
_broad_overrides_cache: List[Dict[str, str]] | None = None


def _domain_tokens_path() -> Path:
    try:
        from app.rag.config import get_rag_index_dir, get_rag_settings
        base = get_rag_index_dir().parent  # data/
    except Exception:
        base = Path("data")
    return base / "domain_tokens.json"


def _broad_domains_path() -> Path:
    """넓은 도메인(IT, 금융, 의료 등) 설정 JSON 경로."""
    try:
        from app.rag.config import get_rag_index_dir, get_rag_settings

        base = get_rag_index_dir().parent  # data/
    except Exception:
        base = Path("data")
    return base / "domain_tokens_new.json"


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


def _default_broad_domains() -> Dict[str, List[str]]:
    """domain_tokens_new.json이 없을 때 사용할 기본 넓은 도메인 설정."""
    return {
        "IT": ["IT", "정보처리", "개발", "데이터", "빅데이터", "소프트웨어", "컴퓨터", "전산"],
        "금융": ["금융", "재무", "회계", "세무", "투자"],
        "의료": ["의료", "간호", "보건", "의료기사", "병원"],
        "관광/서비스": ["관광", "호텔", "여행", "관광통역", "관광통역안내사", "서비스"],
        "교육": ["교육", "교사", "교육학", "강사"],
        "사회복지": ["사회복지", "복지", "상담"],
        "조리/식품": ["조리", "영양", "식품", "조리사", "영양사"],
        "건설": ["건설", "건축", "토목", "건설기술"],
        "기계/제조": ["기계", "메카트로닉스", "자동화", "제조"],
    }


def load_broad_domains() -> Dict[str, List[str]]:
    """
    data/domain_tokens_new.json 로드.

    구조:
    {
      "domains": {
        "IT": {"tokens": [...]},
        "금융": {"tokens": [...]},
        ...
      }
    }
    반환값은 {"IT": [...], "금융": [...]} 형태.
    overrides는 detect_broad_domains_in_text 내부에서 별도 캐시로 사용.
    """
    global _broad_domains_cache, _broad_overrides_cache
    if _broad_domains_cache is not None:
        return _broad_domains_cache

    path = _broad_domains_path()
    if path.exists():
        try:
            import json

            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            domains = data.get("domains") or {}
            out: Dict[str, List[str]] = {}
            for name, cfg in domains.items():
                tokens = cfg.get("tokens") if isinstance(cfg, dict) else None
                if not isinstance(tokens, list):
                    continue
                # 공백 제거 + 빈 문자열 제거
                cleaned = [str(t).strip() for t in tokens if str(t).strip()]
                if cleaned:
                    out[str(name)] = cleaned
            if out:
                _broad_domains_cache = out
                # overrides: [{"phrase": "...", "domain": "..."}]
                raw_overrides = data.get("overrides") or []
                cleaned_overrides: List[Dict[str, str]] = []
                for item in raw_overrides:
                    if not isinstance(item, dict):
                        continue
                    phrase = str(item.get("phrase") or "").strip()
                    domain = str(item.get("domain") or "").strip()
                    if phrase and domain:
                        cleaned_overrides.append({"phrase": phrase, "domain": domain})
                _broad_overrides_cache = cleaned_overrides
                return _broad_domains_cache
        except Exception:
            # JSON 포맷 문제 등은 조용히 기본값으로 폴백
            pass

    _broad_domains_cache = _default_broad_domains()
    _broad_overrides_cache = []
    return _broad_domains_cache


def get_broad_domains() -> Dict[str, List[str]]:
    """넓은 도메인 설정을 반환 (캐시 사용)."""
    return load_broad_domains()


def _get_broad_overrides() -> List[Dict[str, str]]:
    """domain_tokens_new.json의 overrides 항목을 반환 (없으면 빈 리스트)."""
    # load_broad_domains 호출 시 함께 캐시되므로 여기서는 캐시만 사용.
    global _broad_overrides_cache
    if _broad_overrides_cache is None:
        # 경로만 열어 overrides를 다시 읽는다 (domains 캐시는 그대로 유지).
        path = _broad_domains_path()
        if path.exists():
            try:
                import json

                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                raw_overrides = data.get("overrides") or []
                cleaned_overrides: List[Dict[str, str]] = []
                for item in raw_overrides:
                    if not isinstance(item, dict):
                        continue
                    phrase = str(item.get("phrase") or "").strip()
                    domain = str(item.get("domain") or "").strip()
                    if phrase and domain:
                        cleaned_overrides.append({"phrase": phrase, "domain": domain})
                _broad_overrides_cache = cleaned_overrides
            except Exception:
                _broad_overrides_cache = []
        else:
            _broad_overrides_cache = []
    return _broad_overrides_cache


def detect_broad_domains_in_text(text: str) -> List[str]:
    """
    입력 텍스트에서 넓은 도메인(IT, 금융, 의료 등)을 부분 문자열 기반으로 감지.
    여러 도메인이 매칭되면 중복 제거 후 정렬된 리스트를 반환.
    """
    cfg = get_broad_domains()  # {"IT": [...], ...}
    text = (text or "").strip()
    if not text:
        return []

    # 1) overrides: 특정 구문이 포함되면 지정 도메인만 반환
    overrides = _get_broad_overrides()
    override_found: List[str] = []
    if overrides:
        for item in overrides:
            phrase = item.get("phrase") or ""
            domain = item.get("domain") or ""
            if phrase and domain and phrase in text:
                override_found.append(domain)
        if override_found:
            return sorted(dict.fromkeys(override_found))

    # 2) 일반 토큰: 토큰 길이 내림차순으로 긴 토큰 우선 매칭
    token_domain_pairs: List[tuple[str, str]] = []
    for domain, tokens in cfg.items():
        for token in tokens:
            if token:
                token_domain_pairs.append((token, domain))
    # 긴 토큰이 먼저 매칭되도록 길이 기준 내림차순 정렬
    token_domain_pairs.sort(key=lambda x: len(x[0]), reverse=True)

    found: List[str] = []
    for token, domain in token_domain_pairs:
        if token in text and domain not in found:
            found.append(domain)

    # 순서를 안정적으로 유지하기 위해 dict.fromkeys로 중복 제거 후 정렬
    uniq = sorted(dict.fromkeys(found))
    return uniq


def get_it_tokens() -> frozenset:
    return load_domain_tokens()["it_tokens"]


def get_non_it_tokens() -> frozenset:
    return load_domain_tokens()["non_it_tokens"]


def get_non_it_bm25_expansion() -> Dict[str, List[str]]:
    return load_domain_tokens()["non_it_bm25_expansion"]
