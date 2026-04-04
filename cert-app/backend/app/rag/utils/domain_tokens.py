"""
자격증 직종·도메인 토큰 (IT·디지털 집중 vs 그 외 직종 신호, BM25 확장 등).
data/domain_tokens.json이 있으면 로드, 없으면 하드코딩 기본값 사용.
넓은 도메인은 domain_tokens_new_cert_full.json(전 직종) 우선.
"""
from pathlib import Path
from typing import Any, Dict, List, Optional

# 기본값: export_domain_tokens.py 실행 전 또는 JSON 없을 때 사용
_DEFAULT_IT_TOKENS = frozenset({
    "정보처리", "IT", "개발", "데이터", "DB", "SQL", "빅데이터", "백엔드", "프론트엔드",
    "소프트웨어", "컴퓨터", "시스템", "네트워크", "보안", "클라우드",
    "정보통신", "정보기술개발", "데이터분석", "데이터베이스", "시스템관리", "네트워크관리",
    "정보보안", "산업데이터공학", "시스템운영", "IT서비스",
    # AI/인공지능 계열(도메인 IT 판정 및 soft-score 감점 회피)
    "인공지능", "AI", "머신러닝", "딥러닝", "추천시스템",
})
_DEFAULT_NON_IT_TOKENS = frozenset({
    "관광", "언어", "호텔", "여행", "간호", "의료", "회계", "금융", "건설", "기계",
    "조리", "영양", "사회복지", "교육", "스포츠", "미용", "부동산", "물류", "농업",
    "수산", "식품", "경제", "보건", "통역", "번역", "디자인", "예술", "경영", "마케팅", "전산",
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
_domain_to_top_cache: Optional[Dict[str, str]] = None


def _domain_tokens_path() -> Path:
    try:
        from app.rag.config import get_rag_index_dir, get_rag_settings
        base = get_rag_index_dir().parent  # data/
    except Exception:
        base = Path("data")
    return base / "domain_tokens.json"


def _broad_domains_base() -> Path:
    """data/ 디렉터리 경로 (get_rag_index_dir().parent)."""
    try:
        from app.rag.config import get_rag_index_dir
        return get_rag_index_dir().parent
    except Exception:
        return Path("data")


DOMAIN_TOKENS_BROAD_FILE = "domain_tokens_new_cert_full.json"


def _broad_domains_improved_candidates() -> List[Path]:
    """
    domain_tokens_new_cert_full.json 후보 경로 목록.
    백엔드 data/ 디렉터리를 확실히 찾기 위해 (1) 패키지 기준 경로, (2) RAG 설정 기준 경로 순으로 시도.
    """
    candidates: List[Path] = []
    # 1) 이 모듈 기준 backend/data/ (app/rag/utils/domain_tokens.py -> parents[3] = backend)
    try:
        pkg_data = Path(__file__).resolve().parents[3] / "data" / DOMAIN_TOKENS_BROAD_FILE
        if pkg_data.is_file():
            candidates.append(pkg_data)
    except Exception:
        pass
    # 2) RAG 설정의 data/ 디렉터리
    try:
        base = _broad_domains_base()
        improved = base / DOMAIN_TOKENS_BROAD_FILE
        if improved.is_file() and improved not in candidates:
            candidates.append(improved)
    except Exception:
        pass
    return candidates


def _broad_domains_path() -> Path:
    """
    넓은 도메인 설정 JSON 경로.
    domain_tokens_new_improved_v2.json 후보 경로 중 첫 번째를 사용한다.
    후보가 하나도 없으면 RAG data 디렉터리 기준 v2 파일을 가리키며,
    파일이 실제로 없으면 load_broad_domains() 단계에서 기본값으로 폴백된다.
    """
    for path in _broad_domains_improved_candidates():
        return path
    base = _broad_domains_base()
    return base / DOMAIN_TOKENS_BROAD_FILE


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
    """
    domain_tokens_new_cert_full.json이 없을 때 사용할 기본 넓은 도메인 설정.

    상위 라벨은 문서에서만 사용하고, 코드·슬롯에서는 세부 라벨을 직접 사용한다.
    세부 라벨 목록:
    - IT/디지털: 데이터/AI, 소프트웨어개발, IT인프라/보안
    - 엔지니어링/산업기술: 전기/전자, 기계/제조, 건설/건축, 환경/안전
    - 경영/비즈니스: 금융/회계, 경영/사무, 유통/물류/무역, 법률, 공공/행정
    - 보건/복지: 의료/보건, 사회복지/상담
    - 교육/생활서비스: 교육, 관광/항공/호텔, 조리/식품, 미용/패션
    - 크리에이티브/미디어: 디자인, 콘텐츠/미디어
    - 1차산업/자원: 농림/축산/수산
    """
    return {
        # IT/디지털
        "데이터/AI": [
            "데이터 분석",
            "데이터분석",
            "데이터 분석가",
            "데이터사이언스",
            "데이터 사이언스",
            "AI",
            "인공지능",
            "머신러닝",
            "딥러닝",
            "빅데이터",
            "통계",
            "추천시스템",
            "SQL",
            "ADsP",
            "ADP",
        ],
        "소프트웨어개발": [
            "개발",
            "프로그래밍",
            "코딩",
            "웹",
            "앱",
            "백엔드",
            "프론트엔드",
            "풀스택",
            "소프트웨어",
            "서버",
            "API",
            "자바",
            "파이썬",
            "리액트",
            "스프링",
            "게임 개발",
            "게임개발",
        ],
        "IT인프라/보안": [
            "보안",
            "정보보안",
            "네트워크",
            "서버",
            "시스템",
            "클라우드",
            "인프라",
            "AWS",
            "리눅스",
            "해킹",
            "관제",
            "운영",
        ],
        # 엔지니어링/산업기술
        "전기/전자": [
            "전기",
            "전자",
            "제어",
            "회로",
            "PLC",
            "자동제어",
            "반도체",
            "설비 전장",
            "계장",
            "전장",
        ],
        "기계/제조": [
            "기계",
            "제조",
            "생산",
            "품질",
            "공정",
            "설비",
            "기계설계",
            "CAD",
            "CAM",
            "용접",
            "CNC",
            "금형",
            "산업설비",
        ],
        "건설/건축": [
            "건설",
            "건축",
            "토목",
            "실내건축",
            "시공",
            "구조",
            "현장",
            "인테리어",
            "인테리어시공",
        ],
        "환경/안전": [
            "안전",
            "산업안전",
            "위험물",
            "환경",
            "대기",
            "수질",
            "폐기물",
            "소방",
            "보건안전",
        ],
        # 경영/비즈니스
        "금융/회계": [
            "회계",
            "세무",
            "재무",
            "금융",
            "자산관리",
            "세금",
            "원가",
            "결산",
            "회계처리",
        ],
        "경영/사무": [
            "사무",
            "행정사무",
            "총무",
            "인사",
            "비서",
            "문서작성",
            "오피스",
            "경영지원",
            "기업관리",
            "전산",
        ],
        "유통/물류/무역": [
            "유통",
            "물류",
            "무역",
            "구매",
            "수출입",
            "통관",
            "재고",
            "SCM",
            "포워딩",
        ],
        "법률": [
            "법률",
            "법무",
            "계약",
            "행정심판",
            "특허",
            "지식재산",
            "소송지원",
            "준법",
        ],
        "공공/행정": [
            "공공",
            "행정",
            "공기업",
            "공무원",
            "행정실무",
            "정책지원",
            "기관행정",
        ],
        # 보건/복지
        "의료/보건": [
            "의료",
            "간호",
            "병원",
            "보건",
            "임상",
            "의무기록",
            "병원행정",
            "보건행정",
            "의료정보",
        ],
        "사회복지/상담": [
            "사회복지",
            "복지",
            "상담",
            "복지관",
            "청소년",
            "아동복지",
            "노인복지",
            "사례관리",
            "심리상담",
        ],
        # 교육/생활서비스
        "교육": [
            "교육",
            "교사",
            "교직",
            "강사",
            "평생교육",
            "직업훈련",
            "학습지도",
        ],
        "관광/항공/호텔": [
            "관광",
            "여행",
            "호텔",
            "항공",
            "승무원",
            "서비스",
            "예약",
            "프런트",
            "관광통역",
        ],
        "조리/식품": [
            "조리",
            "요리",
            "제과",
            "제빵",
            "식품",
            "바리스타",
            "카페",
            "영양",
            "급식",
        ],
        "미용/패션": [
            "미용",
            "헤어",
            "헤어디자인",
            "메이크업",
            "네일",
            "피부",
            "패션",
            "스타일리스트",
            "코디",
        ],
        # 크리에이티브/미디어
        "디자인": [
            "디자인",
            "시각디자인",
            "UI",
            "UX",
            "편집디자인",
            "그래픽",
            "브랜딩",
            "제품디자인",
            "산업디자인",
        ],
        "콘텐츠/미디어": [
            "콘텐츠",
            "영상",
            "편집",
            "방송",
            "미디어",
            "유튜브",
            "게임",
            "3D",
            "모션그래픽",
            "애니메이션",
        ],
        # 1차산업/자원
        "농림/축산/수산": [
            "농업",
            "축산",
            "수산",
            "산림",
            "조경",
            "원예",
            "스마트팜",
            "양식",
        ],
    }


def load_broad_domains() -> Dict[str, List[str]]:
    """
    domain_tokens_new_improved_v4_full.json 로드.

    지원 구조:
    - domains: { "세부도메인": { "tokens": [...], "top_domain": "상위도메인" }, ... }
    - domains: { "도메인": [...], ... }  (리스트 직접)
    - overrides: [ {"phrase": "...", "domain": "..."}, ... ]
    - top_domains: { "상위도메인": ["세부1", "세부2"] }  (파서는 참고만, 반환값에는 미사용)
    반환값은 {"세부도메인": [tokens], ...} 형태.
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
                if isinstance(cfg, list):
                    tokens = cfg
                elif isinstance(cfg, dict):
                    tokens = cfg.get("tokens")
                else:
                    continue
                if not isinstance(tokens, list):
                    continue
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
    """넓은 도메인 설정을 반환 (캐시 사용). domain_tokens_new_improved_v2.json 기반."""
    return load_broad_domains()


def _load_domain_to_top() -> Dict[str, str]:
    """JSON에서 세부 도메인 -> 상위 도메인 매핑 로드. 재질의 정규화도메인(상위)용."""
    global _domain_to_top_cache
    if _domain_to_top_cache is not None:
        return _domain_to_top_cache
    path = _broad_domains_path()
    out: Dict[str, str] = {}
    if path.is_file():
        try:
            import json
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            domains = data.get("domains") or {}
            for name, cfg in domains.items():
                if isinstance(cfg, dict):
                    top = (cfg.get("top_domain") or "").strip()
                    if top:
                        out[str(name).strip()] = top
            if not out:
                top_domains = data.get("top_domains") or {}
                for top, subs in top_domains.items():
                    if not isinstance(subs, list):
                        continue
                    for sub in subs:
                        if sub:
                            out[str(sub).strip()] = str(top).strip()
        except Exception:
            pass
    _domain_to_top_cache = out
    return _domain_to_top_cache


def get_top_domain_for_domain(domain: str) -> Optional[str]:
    """세부 도메인에 대한 상위 도메인(정규화도메인) 반환. JSON 우선, 없으면 dataset/domain.txt."""
    if not (domain or "").strip():
        return None
    d = (domain or "").strip()
    top = _load_domain_to_top().get(d)
    if top:
        return top
    try:
        from app.rag.utils.domain_txt_loader import get_domain_to_top_from_domain_txt
        return get_domain_to_top_from_domain_txt().get(d)
    except Exception:
        return None


def get_domain_keywords(domain: str, max_terms: int = 20) -> List[str]:
    """도메인 대표 키워드. dataset/domain.txt 우선, 없으면 JSON(get_broad_domains) 기반."""
    if not (domain or "").strip():
        return []
    d = (domain or "").strip()
    try:
        from app.rag.utils.domain_txt_loader import get_domain_keywords_from_domain_txt
        kw = get_domain_keywords_from_domain_txt(d, max_terms=max_terms)
        if kw:
            return kw
    except Exception:
        pass
    tokens = get_broad_domains().get(d) or []
    return list(tokens)[:max_terms]


def get_broad_domain_priority_order() -> List[str]:
    """
    복수 도메인 감지 시 우선 선택할 세부 도메인 순서.
    domain_tokens_new_cert_full.json 의 domains 키 순서를 그대로 사용한다.
    """
    return list(get_broad_domains().keys())


def _get_broad_overrides() -> List[Dict[str, str]]:
    """domain_tokens_new_cert_full.json의 overrides 항목을 반환 (없으면 빈 리스트)."""
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
