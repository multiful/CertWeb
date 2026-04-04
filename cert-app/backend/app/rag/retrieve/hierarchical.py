"""
Hierarchical retrieval (child -> parent 확장).

- child: certificates_vectors.content를 문단/구분자 기준으로 분할한 가상 청크
- parent: qual_id 단위(최종 chunk_id는 qual_id:0으로 환원)
"""
from __future__ import annotations

import re
from typing import Dict, List, Tuple

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.rag.config import get_rag_settings
from app.rag.index.bm25_index import BM25Index


_CACHE_KEY: Tuple[int, int] | None = None
_CACHE_INDEX: BM25Index | None = None
_CACHE_PARENT_BY_CHILD: Dict[str, int] = {}

_SECTION_SPLIT_RE = re.compile(
    r"(?:\n{2,}|\s*\|\s*|(?=(?:응시자격|시험과목|활용직무|난이도|추천\s*대상)\s*[:：]))"
)


def _split_child_chunks(content: str) -> List[str]:
    raw = _SECTION_SPLIT_RE.split((content or "").strip())
    out: List[str] = []
    for part in raw:
        p = (part or "").strip()
        if len(p) < 15:
            continue
        out.append(p)
    if out:
        return out
    fallback = (content or "").strip()
    return [fallback] if fallback else []


def _ensure_hierarchical_index(db: Session) -> Tuple[BM25Index, Dict[str, int]]:
    global _CACHE_KEY, _CACHE_INDEX, _CACHE_PARENT_BY_CHILD
    stat = db.execute(
        text(
            """
            SELECT COUNT(*)::int AS cnt, COALESCE(MAX(EXTRACT(EPOCH FROM updated_at))::bigint, 0) AS max_updated
            FROM certificates_vectors
            """
        )
    ).fetchone()
    key = (int(getattr(stat, "cnt", 0) or 0), int(getattr(stat, "max_updated", 0) or 0))
    if _CACHE_INDEX is not None and _CACHE_KEY == key:
        return _CACHE_INDEX, _CACHE_PARENT_BY_CHILD

    rows = db.execute(
        text(
            """
            SELECT qual_id, COALESCE(chunk_index, 0) AS chunk_index, COALESCE(content, '') AS content
            FROM certificates_vectors
            WHERE content IS NOT NULL AND TRIM(content) != ''
            """
        )
    ).fetchall()

    docs: List[dict] = []
    parent_by_child: Dict[str, int] = {}
    for r in rows:
        qual_id = int(getattr(r, "qual_id"))
        cidx = int(getattr(r, "chunk_index"))
        content = str(getattr(r, "content") or "")
        child_parts = _split_child_chunks(content)
        for i, part in enumerate(child_parts):
            child_id = f"{qual_id}:{cidx}:child:{i}"
            docs.append({"chunk_id": child_id, "text": part})
            parent_by_child[child_id] = qual_id

    idx = BM25Index()
    s = get_rag_settings()
    idx.build(
        docs,
        use_korean_ngram=bool(getattr(s, "RAG_BM25_USE_KOREAN_NGRAM", True)),
        k1=float(getattr(s, "RAG_BM25_K1", 1.5) or 1.5),
        b=float(getattr(s, "RAG_BM25_B", 0.75) or 0.75),
    )
    _CACHE_KEY = key
    _CACHE_INDEX = idx
    _CACHE_PARENT_BY_CHILD = parent_by_child
    return idx, parent_by_child


def hierarchical_parent_candidates(
    db: Session,
    query: str,
    top_k: int,
) -> List[Tuple[str, float]]:
    """
    child BM25 검색 후 parent(qual_id:0) 점수로 환원.
    환원 점수: child 최댓값 + (중복 child 보너스 0.08 * (count-1)).
    """
    idx, parent_map = _ensure_hierarchical_index(db)
    child_hits = idx.search(query, k=max(top_k, 10))
    by_parent: Dict[int, Tuple[float, int]] = {}
    for child_id, score in child_hits:
        qid = parent_map.get(child_id)
        if qid is None:
            continue
        prev = by_parent.get(qid)
        if prev is None:
            by_parent[qid] = (float(score), 1)
        else:
            by_parent[qid] = (max(prev[0], float(score)), prev[1] + 1)

    out: List[Tuple[str, float]] = []
    for qid, (best, cnt) in by_parent.items():
        agg = best + (0.08 * max(0, cnt - 1))
        out.append((f"{qid}:0", agg))
    out.sort(key=lambda x: -x[1])
    return out[:top_k]

