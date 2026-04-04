"""
Contextual child retrieval.

- child row: (qual_id, child_index, chunk_text, chunk_context, contextual_text, embedding)
- query 시 child 벡터 검색 후 parent(qual_id:0) 점수로 환원
"""
from __future__ import annotations

from collections import defaultdict
from typing import Dict, List, Tuple

from sqlalchemy import text
from sqlalchemy.orm import Session


def contextual_child_search(
    db: Session,
    query_embedding: List[float],
    top_k: int,
    similarity_threshold: float = 0.0,
) -> List[Tuple[str, float]]:
    """
    contextual child 검색 후 parent 기준으로 점수 집계.

    반환: [(f"{qual_id}:0", aggregated_score), ...]
    """
    if not query_embedding:
        return []
    max_distance = 1.0 - max(0.0, min(1.0, float(similarity_threshold)))
    try:
        rows = db.execute(
            text(
                """
                SELECT qual_id, child_index, (1 - (embedding <=> :vec)) AS similarity
                FROM certificates_vectors_contextual
                WHERE embedding IS NOT NULL
                  AND (embedding <=> :vec) <= :max_distance
                ORDER BY embedding <=> :vec
                LIMIT :limit
                """
            ),
            {
                "vec": str(query_embedding),
                "max_distance": max_distance,
                "limit": max(int(top_k), 1),
            },
        ).fetchall()
    except Exception:
        return []

    # parent 점수 집계:
    # - max(similarity): 대표 문맥 적합도
    # - + 작은 coverage bonus: 같은 qual에서 여러 child hit 시 보강
    by_parent_scores: Dict[int, List[float]] = defaultdict(list)
    for r in rows:
        qid = int(getattr(r, "qual_id"))
        sim = float(getattr(r, "similarity", 0.0) or 0.0)
        by_parent_scores[qid].append(sim)

    merged: List[Tuple[str, float]] = []
    for qid, sims in by_parent_scores.items():
        best = max(sims) if sims else 0.0
        coverage_bonus = 0.04 * max(0, len(sims) - 1)
        merged.append((f"{qid}:0", best + coverage_bonus))
    merged.sort(key=lambda x: -x[1])
    return merged[:top_k]

