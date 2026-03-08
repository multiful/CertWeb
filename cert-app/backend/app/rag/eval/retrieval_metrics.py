"""Retrieval 지표: Recall@k, Precision@k, MRR, nDCG@k. + qual_id 단위 버전."""
import math
from typing import List, Set


def _chunk_id_to_qual_id(cid: str) -> int | None:
    if not cid or ":" not in cid:
        return None
    try:
        return int(cid.split(":")[0])
    except ValueError:
        return None


def recall_at_k(retrieved_ids: List[str], gold_ids: Set[str], k: int) -> float:
    """Recall@k: gold 중 상위 k개 안에 있는 비율."""
    if not gold_ids:
        return 0.0
    top_k = set(retrieved_ids[:k])
    hits = len(gold_ids & top_k)
    return hits / len(gold_ids)


def precision_at_k(retrieved_ids: List[str], gold_ids: Set[str], k: int) -> float:
    """Precision@k: 상위 k개 중 정답(gold)에 해당하는 비율. k=0이면 0."""
    if k <= 0:
        return 0.0
    top_k = retrieved_ids[:k]
    if not top_k:
        return 0.0
    hits = sum(1 for cid in top_k if cid in gold_ids)
    return hits / len(top_k)


def mrr(retrieved_ids: List[str], gold_ids: Set[str]) -> float:
    """Mean Reciprocal Rank: 첫 번째 정답이 나온 순위의 역수."""
    if not gold_ids:
        return 0.0
    for i, cid in enumerate(retrieved_ids):
        if cid in gold_ids:
            return 1.0 / (i + 1)
    return 0.0


def hit_count_at_k(retrieved_ids: List[str], gold_ids: Set[str], k: int) -> int:
    """상위 k개 안에 있는 정답(chunk_id) 개수. Hit@k 지표의 질의당 값."""
    if not gold_ids or k <= 0:
        return 0
    top_k = set(retrieved_ids[:k])
    return len(gold_ids & top_k)


def success_at_k(retrieved_ids: List[str], gold_ids: Set[str], k: int) -> float:
    """상위 k개 안에 정답이 1개 이상 있으면 1, 없으면 0. Success@k 지표의 질의당 값."""
    if not gold_ids or k <= 0:
        return 0.0
    return 1.0 if recall_at_k(retrieved_ids, gold_ids, k) > 0 else 0.0


def mrr_at_k(retrieved_ids: List[str], gold_ids: Set[str], k: int) -> float:
    """상위 k개까지만 보고 계산한 MRR. k개 밖에 정답만 있으면 0."""
    if not gold_ids or k <= 0:
        return 0.0
    for i, cid in enumerate(retrieved_ids[:k]):
        if cid in gold_ids:
            return 1.0 / (i + 1)
    return 0.0


def first_relevant_rank(retrieved_ids: List[str], gold_ids: Set[str]) -> int | None:
    """첫 번째 정답이 나온 순위(1-based). 없으면 None. 상위권 밀도 지표용."""
    if not gold_ids:
        return None
    for i, cid in enumerate(retrieved_ids):
        if cid in gold_ids:
            return i + 1
    return None


def recall_at_k_qual(retrieved_ids: List[str], gold_qual_ids: Set[int], k: int) -> float:
    """Recall@k (qual_id 단위): 상위 k개 내 고유 qual_id 중 gold_qual_ids와 겹치는 비율."""
    if not gold_qual_ids:
        return 0.0
    seen = set()
    for cid in retrieved_ids[:k]:
        qid = _chunk_id_to_qual_id(cid)
        if qid is not None:
            seen.add(qid)
    hits = len(gold_qual_ids & seen)
    return hits / len(gold_qual_ids)


def mrr_qual(retrieved_ids: List[str], gold_qual_ids: Set[int]) -> float:
    """MRR (qual_id 단위): 첫 번째로 gold_qual_ids에 해당하는 qual_id가 나온 순위의 역수."""
    if not gold_qual_ids:
        return 0.0
    for i, cid in enumerate(retrieved_ids):
        qid = _chunk_id_to_qual_id(cid)
        if qid is not None and qid in gold_qual_ids:
            return 1.0 / (i + 1)
    return 0.0


def ndcg_at_k(retrieved_ids: List[str], gold_ids: Set[str], k: int) -> float:
    """
    nDCG@k (Normalized Discounted Cumulative Gain). 순위 품질 지표.
    Binary relevance: rel=1 if chunk in gold else 0. DCG = sum(rel_i / log2(rank_i+1)), IDCG = ideal DCG.
    """
    if not gold_ids or k <= 0:
        return 0.0
    top_k = retrieved_ids[:k]
    # relevance vector (1 if in gold else 0)
    rel = [1.0 if cid in gold_ids else 0.0 for cid in top_k]
    # DCG@k
    dcg = sum(r / _log2(i + 2) for i, r in enumerate(rel))  # rank 1-based -> index+2
    # IDCG: ideal = all 1s at top, num_relevant = min(|gold|, k)
    num_rel = min(len(gold_ids), k)
    if num_rel == 0:
        return 0.0
    idcg = sum(1.0 / _log2(i + 2) for i in range(num_rel))
    if idcg <= 0:
        return 0.0
    return dcg / idcg


def _log2(x: float) -> float:
    return math.log2(x) if x > 0 else 1.0
