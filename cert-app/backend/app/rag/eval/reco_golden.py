"""
추천 골든셋(reco) 형식 지원: query_text + gold_ranked [{cert_name, relevance}]
→ question + gold_chunk_ids [qual_id:0] 로 변환하여 기존 RAG 평가에 사용.
cert_name → qual_id: (1) 별칭 리다이렉트 (2) DB qual_name 정확 일치 (3) 공백·구두점 무시 일치
(4) 골든 문자열이 qual_name 부분문자열 (5) compact 키가 qual_name compact에 포함 (긴 키만).
"""
import re
from typing import Any, Dict, List, Set

from sqlalchemy.orm import Session
from sqlalchemy import text


def _compact_match_key(s: str) -> str:
    """공백·마침표·중점 등 제거한 비교 키 (한글 lower 무의미)."""
    if not s:
        return ""
    return re.sub(r"[\s\.・·]+", "", (s or "").strip())


# 골든 expected_certs 표기 → DB qualification.qual_name 과 동일한 문자열로 통일 (필요 시만 추가)
RECO_GOLDEN_EXPECTED_CERT_ALIASES: Dict[str, str] = {
    # 예: 구형 표기 → 현행 자격증명
}


def _qual_id_to_name_map(db: Session) -> Dict[int, str]:
    rows = db.execute(text("SELECT qual_id, qual_name FROM qualification")).fetchall()
    return {r.qual_id: (r.qual_name or "").strip() for r in rows}


def _cert_name_to_qual_ids(cert_name: str, qual_id_to_name: Dict[int, str]) -> List[int]:
    """
    cert_name에 해당하는 qual_id 목록.
    정확 일치 → compact 일치 → 부분문자열(짧은 qual_name 우선) → compact 부분포함(키 길이 하한).
    """
    c = (cert_name or "").strip()
    if not c or not qual_id_to_name:
        return []

    c = RECO_GOLDEN_EXPECTED_CERT_ALIASES.get(c, c)

    exact = [qid for qid, qname in qual_id_to_name.items() if (qname or "").strip() == c]
    if exact:
        # 동일 qual_name이 DB에 중복 저장된 경우가 있어 gold 확장(요구 항목 증가)으로 이어질 수 있음.
        # 평가에서는 "해당 cert_name에 대해 가장 일관된 1개"만 골라야 Success@4가 과도하게 깎이지 않는다.
        return [sorted(exact)[0]]

    c_key = _compact_match_key(c)
    if c_key and len(c_key) >= 2:
        exact_c = [
            qid
            for qid, qname in qual_id_to_name.items()
            if _compact_match_key(qname or "") == c_key
        ]
        if exact_c:
            return [sorted(exact_c)[0]]

    candidates = [(qid, qname) for qid, qname in qual_id_to_name.items() if c in (qname or "")]
    if not candidates and c_key and len(c_key) >= 6:
        for qid, qname in qual_id_to_name.items():
            qn = (qname or "").strip()
            if not qn:
                continue
            qk = _compact_match_key(qn)
            if c_key in qk:
                candidates.append((qid, qn))
    if not candidates:
        return []
    candidates.sort(key=lambda x: len(x[1]))
    min_len = len(candidates[0][1])
    # min_len 후보 중에서도 중복 qual_id가 여러 개면 gold를 확장시키지 않도록 1개만 선택
    best = sorted([qid for qid, qname in candidates if len(qname) == min_len])[0]
    return [best]


def cert_names_to_gold_chunk_ids(
    db: Session,
    gold_ranked: List[Dict[str, Any]],
    min_relevance: int = 1,
    qual_id_to_name: Dict[int, str] | None = None,
) -> Set[str]:
    """
    gold_ranked [{cert_name, relevance}, ...] → 정답 qual_id들의 청크 id 집합 {"qual_id:0", ...}.
    relevance >= min_relevance 인 cert_name만 사용. DB에 없는 자격증명/선택 항목은 무시.
    """
    if qual_id_to_name is None:
        qual_id_to_name = _qual_id_to_name_map(db)
    out: Set[str] = set()
    for g in gold_ranked or []:
        if int(g.get("relevance", 0)) < min_relevance:
            continue
        cert_name = (g.get("cert_name") or "").strip()
        if not cert_name:
            continue
        qids = _cert_name_to_qual_ids(cert_name, qual_id_to_name)
        for qid in qids:
            out.add(f"{qid}:0")
    return out


def normalize_reco_golden(golden: List[Dict[str, Any]], db: Session) -> List[Dict[str, Any]]:
    """
    reco 형식 행(query_text, gold_ranked)이 있으면 question, gold_chunk_ids로 변환한 새 리스트 반환.
    profile-aware 확장: expected_certs(자격증명 리스트)만 있으면 gold_ranked로 변환 후 동일 처리.
    이미 gold_chunk_ids가 있는 행은 그대로 유지.
    """
    qual_id_to_name = _qual_id_to_name_map(db)
    out: List[Dict[str, Any]] = []
    for row in golden:
        r = dict(row)
        gold_ranked = row.get("gold_ranked")
        if gold_ranked is None and row.get("expected_certs"):
            # profile-aware 포맷: expected_certs → gold_ranked
            expected = row["expected_certs"]
            if isinstance(expected, list):
                gold_ranked = [{"cert_name": (c if isinstance(c, str) else c.get("cert_name", "")), "relevance": 1} for c in expected]
            else:
                gold_ranked = []
            r["gold_ranked"] = gold_ranked
        if (r.get("gold_ranked") is not None) and not r.get("gold_chunk_ids"):
            r["gold_chunk_ids"] = list(cert_names_to_gold_chunk_ids(
                db, r["gold_ranked"], min_relevance=1, qual_id_to_name=qual_id_to_name
            ))
            r["question"] = r.get("query_text") or r.get("question") or ""
        out.append(r)
    return out
