"""
dataset/domain.txt 파서.
상위 도메인 목록, 세부->상위 매핑, 세부 도메인별 대표 키워드를 파일에서 로드.
DB에 상위 도메인/도메인 키워드를 올리지 않고 이 파일만 유지보수하면 됨.
"""
import re
from pathlib import Path
from typing import Dict, List, Optional, FrozenSet

_domain_txt_path: Optional[Path] = None
_top_domains_cache: Optional[FrozenSet[str]] = None
_domain_to_top_cache: Optional[Dict[str, str]] = None
_domain_keywords_cache: Optional[Dict[str, List[str]]] = None


def _domain_txt_path_resolve() -> Path:
    global _domain_txt_path
    if _domain_txt_path is not None:
        return _domain_txt_path
    # backend/dataset/domain.txt (app/rag/utils -> parents[3] = backend)
    try:
        base = Path(__file__).resolve().parents[3] / "dataset"
        p = base / "domain.txt"
        if p.is_file():
            _domain_txt_path = p
            return _domain_txt_path
    except Exception:
        pass
    _domain_txt_path = Path("dataset") / "domain.txt"
    return _domain_txt_path


def _load_from_domain_txt() -> tuple[Dict[str, str], Dict[str, List[str]]]:
    """
    domain.txt 파싱.
    반환: (domain_to_top: 세부->상위, domain_keywords: 세부->[키워드])
    """
    global _domain_to_top_cache, _domain_keywords_cache
    path = _domain_txt_path_resolve()
    domain_to_top: Dict[str, str] = {}
    domain_keywords: Dict[str, List[str]] = {}

    if not path.is_file():
        _domain_to_top_cache = domain_to_top
        _domain_keywords_cache = domain_keywords
        return domain_to_top, domain_keywords

    try:
        text = path.read_text(encoding="utf-8")
    except Exception:
        _domain_to_top_cache = domain_to_top
        _domain_keywords_cache = domain_keywords
        return domain_to_top, domain_keywords

    lines = text.splitlines()
    current_top: Optional[str] = None
    in_block1 = False

    # 1) "상위 라벨 -> 세부 라벨" 블록만 (1. 상위 ~ 2. 트리 직전)
    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("1. 상위"):
            in_block1 = True
            continue
        if stripped.startswith("2."):
            break
        if not in_block1:
            continue
        if re.match(r"^\d+\.\s", stripped):
            continue
        if stripped.startswith("["):
            continue
        if stripped.startswith("- "):
            sub = stripped[2:].strip()
            if sub and current_top and not sub.startswith("대표"):
                domain_to_top[sub] = current_top
            continue
        # 상위 도메인: 한 줄, 슬래시 포함(예: IT/디지털) 또는 한글 조합, 너무 길지 않음
        if stripped and not stripped.startswith("-") and len(stripped) < 50 and ":" not in stripped:
            current_top = stripped
            continue

    # 2) "3. 세부 라벨별 상세 정의" 블록: "(N) 세부도메인" 다음 "- 대표 키워드" 블록
    in_section3 = False
    current_domain: Optional[str] = None
    in_keywords = False
    keywords: List[str] = []

    for i, line in enumerate(lines):
        stripped = line.strip()
        if "3. 세부 라벨별 상세 정의" in stripped:
            in_section3 = True
            continue
        if in_section3 and stripped.startswith("4."):
            break
        if not in_section3:
            continue

        if stripped.startswith("["):
            in_keywords = False
            current_domain = None
            continue
        m = re.match(r"^\(\d+\)\s+(.+)$", stripped)
        if m:
            if current_domain and keywords:
                domain_keywords[current_domain] = list(keywords)
            name = m.group(1).strip()
            if " [" in name:
                name = name.split(" [")[0].strip()
            current_domain = name
            keywords = []
            in_keywords = False
            continue
        if stripped == "- 대표 키워드":
            in_keywords = True
            continue
        if stripped.startswith("- 대표"):
            in_keywords = False
            if current_domain and keywords:
                domain_keywords[current_domain] = list(keywords)
                keywords = []
            continue
        if in_keywords and current_domain and stripped and not stripped.startswith("-"):
            keywords.append(stripped)
            continue

    if current_domain and keywords:
        domain_keywords[current_domain] = list(keywords)

    _domain_to_top_cache = domain_to_top
    _domain_keywords_cache = domain_keywords
    return domain_to_top, domain_keywords


def get_top_domains_from_domain_txt() -> FrozenSet[str]:
    """domain.txt 기준 상위 도메인 목록 (세부->상위 맵의 값 집합)."""
    global _top_domains_cache
    if _top_domains_cache is not None:
        return _top_domains_cache
    domain_to_top, _ = _load_from_domain_txt()
    tops = frozenset(domain_to_top.values()) if domain_to_top else frozenset()
    _top_domains_cache = tops
    return _top_domains_cache


def get_domain_to_top_from_domain_txt() -> Dict[str, str]:
    """domain.txt 기준 세부 도메인 -> 상위 도메인 매핑."""
    domain_to_top, _ = _load_from_domain_txt()
    return domain_to_top


def get_domain_keywords_from_domain_txt(domain: str, max_terms: int = 20) -> List[str]:
    """domain.txt 기준 세부 도메인 대표 키워드. 없으면 빈 리스트."""
    _, domain_keywords = _load_from_domain_txt()
    d = (domain or "").strip()
    if not d:
        return []
    kw = domain_keywords.get(d) or []
    return list(kw)[:max_terms]


def clear_domain_txt_cache() -> None:
    """캐시 초기화 (domain.txt 수정 후 테스트 시)."""
    global _top_domains_cache, _domain_to_top_cache, _domain_keywords_cache
    _top_domains_cache = None
    _domain_to_top_cache = None
    _domain_keywords_cache = None
