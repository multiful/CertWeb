"""
추천 골든셋(reco) 형식 지원: query_text + gold_ranked [{cert_name, relevance}]
→ question + gold_chunk_ids [qual_id:0] 로 변환하여 기존 RAG 평가에 사용.
cert_name → qual_id 매칭은 정확 일치 우선, 없으면 qual_name 포함 시 가장 짧은 것만 사용.
"""
from typing import Any, Dict, List, Set

from sqlalchemy.orm import Session
from sqlalchemy import text


def _qual_id_to_name_map(db: Session) -> Dict[int, str]:
    rows = db.execute(text("SELECT qual_id, qual_name FROM qualification")).fetchall()
    return {r.qual_id: (r.qual_name or "").strip() for r in rows}


def _cert_name_to_qual_ids(cert_name: str, qual_id_to_name: Dict[int, str]) -> List[int]:
    """
    cert_name에 해당하는 qual_id 목록. 정확 일치 우선, 없으면 qual_name에 cert_name이 포함된 것 중 가장 짧은 것만.
    """
    c = (cert_name or "").strip()
    if not c or not qual_id_to_name:
        return []

    exact = [qid for qid, qname in qual_id_to_name.items() if (qname or "") == c]
    if exact:
        return exact

    candidates = [(qid, qname) for qid, qname in qual_id_to_name.items() if c in (qname or "")]
    if not candidates:
        return []
    candidates.sort(key=lambda x: len(x[1]))
    min_len = len(candidates[0][1])
    return [qid for qid, qname in candidates if len(qname) == min_len]


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
