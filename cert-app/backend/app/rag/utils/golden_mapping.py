"""
골든셋 자격증명 → qual_id 매핑 유틸리티.

향상된 매핑 로직:
- 정규화된 문자열 매칭 (공백/특수문자 제거)
- 괄호 내용 추출 (별칭)
- 숫자+급 변형 처리
"""
import re
from typing import Dict, List, Optional

from sqlalchemy import text


def normalize_cert_name(name: str) -> str:
    """자격증명 정규화: 공백/특수문자 제거, 소문자."""
    n = name.lower().strip()
    n = re.sub(r'\s+', '', n)
    n = re.sub(r'[^\uAC00-\uD7A3a-z0-9]', '', n)
    return n


def build_enhanced_name_mapping(db) -> Dict[str, int]:
    """
    향상된 자격증명 매핑 빌드.
    
    반환: {정규화된_이름: qual_id} 딕셔너리
    """
    rows = db.execute(text("SELECT qual_id, qual_name FROM qualification")).fetchall()
    name_to_id = {}
    
    for r in rows:
        qid = r.qual_id
        name = r.qual_name.strip()
        
        # 원본 이름
        name_to_id[name.lower()] = qid
        
        # 정규화된 이름
        normalized = normalize_cert_name(name)
        name_to_id[normalized] = qid
        
        # 괄호 내용 추출
        if "(" in name:
            short = name.split("(")[0].strip().lower()
            name_to_id[short] = qid
            name_to_id[normalize_cert_name(short)] = qid
            
            inside = name.split("(")[1].split(")")[0].strip().lower()
            name_to_id[inside] = qid
            name_to_id[normalize_cert_name(inside)] = qid
        
        # 기사/산업기사/기능사 변형
        for suffix in ["기사", "산업기사", "기능사"]:
            if name.endswith(suffix):
                base = name[:-len(suffix)].strip()
                name_to_id[base.lower()] = qid
                name_to_id[normalize_cert_name(base)] = qid
        
        # 숫자+급 제거 변형 (리눅스마스터 2급 → 리눅스마스터)
        cleaned = re.sub(r'\s*\d+급$', '', name).strip().lower()
        if cleaned != name.lower():
            name_to_id[cleaned] = qid
            name_to_id[normalize_cert_name(cleaned)] = qid
    
    return name_to_id


def fuzzy_match_cert_name(cert_name: str, name_to_id: Dict[str, int]) -> Optional[int]:
    """유연한 자격증명 매칭."""
    cn = cert_name.strip()
    cn_lower = cn.lower()
    
    # 1. 직접 매칭
    if cn_lower in name_to_id:
        return name_to_id[cn_lower]
    
    # 2. 정규화 매칭
    normalized = normalize_cert_name(cn)
    if normalized in name_to_id:
        return name_to_id[normalized]
    
    # 3. 괄호 제거 후 매칭
    if "(" in cn:
        main_part = cn.split("(")[0].strip().lower()
        if main_part in name_to_id:
            return name_to_id[main_part]
        if normalize_cert_name(main_part) in name_to_id:
            return name_to_id[normalize_cert_name(main_part)]
        
        # 괄호 안 내용 매칭
        inside = cn.split("(")[1].split(")")[0].strip().lower()
        if inside in name_to_id:
            return name_to_id[inside]
    
    # 4. 공백/급 제거 후 매칭
    cleaned = re.sub(r'\s*\d+급$', '', cn).strip().lower()
    cleaned_no_space = re.sub(r'\s+', '', cleaned)
    if cleaned in name_to_id:
        return name_to_id[cleaned]
    if cleaned_no_space in name_to_id:
        return name_to_id[cleaned_no_space]
    
    return None


def normalize_reco_golden_enhanced(golden: List[dict], db) -> List[dict]:
    """
    향상된 cert_name → qual_id 변환 (gold_ranked 형식 골든셋용).
    
    기존 대비 개선:
    - 정규화된 문자열 매칭
    - 괄호 내용 추출
    - 숫자+급 변형 처리
    """
    name_to_id = build_enhanced_name_mapping(db)
    
    out = []
    total_gold = 0
    mapped_gold = 0
    
    for row in golden:
        gold_ranked = row.get("gold_ranked")
        if gold_ranked:
            ids = []
            for g in gold_ranked:
                cn = g.get("cert_name", "").strip()
                total_gold += 1
                qid = fuzzy_match_cert_name(cn, name_to_id)
                if qid:
                    ids.append(f"{qid}:0")
                    mapped_gold += 1
            row["gold_chunk_ids"] = ids
        out.append(row)
    
    # 매핑률 로깅 (선택적)
    if total_gold > 0:
        import logging
        logging.info(f"Golden set mapping: {mapped_gold}/{total_gold} ({mapped_gold/total_gold*100:.1f}%)")
    
    return out
