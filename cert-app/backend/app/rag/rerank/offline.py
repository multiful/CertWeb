"""
오프라인 Rerank: Colab에서 생성한 rerank_scores.jsonl 로드 후 query_id 기준 lookup.
- 입력: rerank_scores.jsonl → {"query_id": "...", "chunk_id": "...", "score": 0.1234}
- query_id 없거나 매칭 실패 시 rerank skip, hybrid 결과 그대로 반환.
"""
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple


def load_rerank_scores(path: Optional[str] = None) -> Dict[str, Dict[str, float]]:
    """
    rerank_scores.jsonl 로드 → { query_id: { chunk_id: score } }
    path 없으면 config RAG_RERANK_SCORES_PATH 사용.
    """
    from app.rag.config import get_rag_settings
    p = path or get_rag_settings().RAG_RERANK_SCORES_PATH
    if not p or not Path(p).exists():
        return {}
    out: Dict[str, Dict[str, float]] = {}
    with open(p, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
                qid = row.get("query_id")
                cid = row.get("chunk_id")
                score = float(row.get("score", 0.0))
                if qid is not None and cid is not None:
                    out.setdefault(qid, {})[cid] = score
            except (json.JSONDecodeError, TypeError):
                continue
    return out


def apply_rerank_scores(
    candidates: List[Tuple[str, float]],
    query_id: str,
    scores_map: Dict[str, Dict[str, float]],
) -> List[Tuple[str, float]]:
    """
    candidates [(chunk_id, _)] 를 query_id에 해당하는 rerank score로 재정렬.
    query_id가 없거나 chunk에 점수가 없으면 원래 순서 유지(점수 0).
    """
    if not candidates or not query_id or query_id not in scores_map:
        return candidates
    chunk_scores = scores_map[query_id]
    scored = [(cid, chunk_scores.get(cid, 0.0)) for cid, _ in candidates]
    scored.sort(key=lambda x: -x[1])
    return scored
