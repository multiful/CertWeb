"""
평가 공통 유틸: 골든 정규화·지표 계산·query_type별 집계를 하나로 고정.
BM25/Vector/Hybrid 모든 평가 스크립트가 이 모듈을 사용해 계산 일관성을 유지한다.
"""
from collections import defaultdict
from typing import Any, Dict, List, Optional, Set

from sqlalchemy.orm import Session

from app.rag.eval.reco_golden import normalize_reco_golden
from app.rag.eval.retrieval_metrics import (
    recall_at_k,
    hit_count_at_k,
    success_at_k,
    mrr,
    mrr_at_k,
    first_relevant_rank,
)


# 표준 k 값: 회수 품질(20) / 노출 품질(4)
DEFAULT_K_RECALL = [5, 10, 20]
DEFAULT_K_TOP = 4


def normalize_gold_labels(
    golden: List[Dict[str, Any]],
    db: Session,
    *,
    drop_empty_gold: bool = True,
) -> List[Dict[str, Any]]:
    """
    expected_certs / gold_ranked → gold_chunk_ids 정규화. 단일 경로로 통일.
    - reco 형식( gold_ranked 또는 expected_certs )이 있으면 gold_chunk_ids 채움.
    - drop_empty_gold=True 이면 정규화 후에도 gold_chunk_ids가 빈 행은 제외.
    """
    if any(
        (row.get("gold_ranked") is not None or row.get("expected_certs"))
        and not row.get("gold_chunk_ids")
        for row in golden
    ):
        golden = normalize_reco_golden(golden, db)
    if drop_empty_gold:
        golden = [
            r for r in golden
            if (r.get("gold_chunk_ids") or []) or not (r.get("gold_ranked") or r.get("expected_certs"))
        ]
    return golden


def compute_recall_hit_mrr(
    retrieved_ids: List[str],
    gold_ids: Set[str],
    k_recall: Optional[List[int]] = None,
    k_top: int = DEFAULT_K_TOP,
) -> Dict[str, Any]:
    """
    단일 질의에 대해 회수·노출 지표 일괄 계산. 모든 평가에서 동일 식 사용.
    - k_recall: Recall@k, Hit@k, Success@k 계산할 k 리스트 (기본 [5,10,20])
    - k_top: 노출 구간 k (기본 4) → Success@4, Hit@4, MRR@4
    반환: Recall@5, Recall@10, Recall@20, Hit@20, Success@20,
          Recall@4, Hit@4, Success@4, MRR, MRR@4, first_relevant_rank(있으면 1-based).
    """
    if not gold_ids:
        out = {
            "Recall@5": 0.0, "Recall@10": 0.0, "Recall@20": 0.0,
            "Hit@20": 0.0, "Success@20": 0.0,
            "Recall@4": 0.0, "Hit@4": 0.0, "Success@4": 0.0,
            "MRR": 0.0, "MRR@4": 0.0, "first_relevant_rank": None,
        }
        for k in (k_recall or DEFAULT_K_RECALL):
            out[f"Recall@{k}"] = 0.0
            out[f"Hit@{k}"] = 0.0
            out[f"Success@{k}"] = 0.0
        return out

    k_recall = k_recall or DEFAULT_K_RECALL
    out: Dict[str, Any] = {}
    for k in k_recall:
        out[f"Recall@{k}"] = recall_at_k(retrieved_ids, gold_ids, k)
        out[f"Hit@{k}"] = float(hit_count_at_k(retrieved_ids, gold_ids, k))
        out[f"Success@{k}"] = success_at_k(retrieved_ids, gold_ids, k)
    out["Hit@20"] = float(hit_count_at_k(retrieved_ids, gold_ids, 20))
    out["Success@20"] = success_at_k(retrieved_ids, gold_ids, 20)
    out["Recall@4"] = recall_at_k(retrieved_ids, gold_ids, k_top)
    out["Hit@4"] = float(hit_count_at_k(retrieved_ids, gold_ids, k_top))
    out["Success@4"] = success_at_k(retrieved_ids, gold_ids, k_top)
    out["MRR"] = mrr(retrieved_ids, gold_ids)
    out["MRR@4"] = mrr_at_k(retrieved_ids, gold_ids, k_top)
    out["first_relevant_rank"] = first_relevant_rank(retrieved_ids, gold_ids)
    return out


def aggregate_metrics_over_queries(
    per_query_metrics: List[Dict[str, Any]],
) -> Dict[str, float]:
    """
    질의별 지표 리스트를 평균 집계. (모든 질의 동일 가중치.)
    """
    if not per_query_metrics:
        return {}
    n = len(per_query_metrics)
    keys_numeric = [k for k in per_query_metrics[0] if k != "first_relevant_rank" and isinstance(per_query_metrics[0].get(k), (int, float))]
    agg = {}
    for k in keys_numeric:
        vals = [m.get(k) for m in per_query_metrics if m.get(k) is not None]
        agg[k] = sum(vals) / n if n and vals else 0.0
    # first_relevant_rank: 평균 (None이면 제외 또는 0 처리)
    fr_vals = [m["first_relevant_rank"] for m in per_query_metrics if m.get("first_relevant_rank") is not None]
    agg["first_relevant_rank_avg"] = sum(fr_vals) / len(fr_vals) if fr_vals else None
    return agg


def group_metrics_by_query_type(
    per_query_rows: List[Dict[str, Any]],
    query_type_key: str = "query_type",
    metrics_keys: Optional[List[str]] = None,
) -> Dict[str, Dict[str, float]]:
    """
    질의별 결과를 query_type별로 묶어 유형별 평균 산출.
    per_query_rows: [ {"query_type": "keyword", "Recall@20": 0.5, "Hit@20": 1, ...}, ... ]
    반환: { "keyword": {"Recall@20": 0.5, "Hit@20": 1.2, "n": 6}, "natural": {...}, ... }
    """
    by_type: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for row in per_query_rows:
        qt = row.get(query_type_key) or "mixed"
        by_type[qt].append(row)

    default_metrics = [
        "Recall@5", "Recall@10", "Recall@20", "Hit@20", "Success@20",
        "Recall@4", "Hit@4", "Success@4", "MRR", "MRR@4",
    ]
    keys = metrics_keys or default_metrics
    result = {}
    for qt, rows in by_type.items():
        n = len(rows)
        agg: Dict[str, Any] = {"n": n}
        for k in keys:
            if k not in rows[0]:
                continue
            vals = [r[k] for r in rows if r.get(k) is not None]
            if vals:
                agg[k] = sum(vals) / len(vals)
        result[qt] = agg
    return result


def is_recommendation_golden(row: Dict[str, Any]) -> bool:
    """recommendation golden: query_text + gold_ranked 중심, expected_certs만 있어도 됨."""
    return bool(row.get("query_text") or row.get("question")) and bool(
        row.get("gold_ranked") is not None or row.get("gold_chunk_ids") or row.get("expected_certs")
    )


def is_profile_golden(row: Dict[str, Any]) -> bool:
    """profile golden: major, grade_level, expected_certs 등 프로필 필드가 있는 골든."""
    return any(
        row.get(k) is not None
        for k in ("major", "grade_level", "favorite_cert_names", "acquired_cert_names", "expected_certs")
    )


def split_golden_by_benchmark(
    golden: List[Dict[str, Any]],
) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    골든을 non-personalized(recommendation) vs profile-aware 로 분리.
    반환: (recommendation_only_rows, profile_rows)
    - recommendation_only: 프로필 없이 일반 추천 질의만 (profile 필드 없거나 비어 있음)
    - profile_rows: major/expected_certs 등 프로필 있는 행
    """
    rec_only = []
    profile = []
    for row in golden:
        if is_profile_golden(row):
            profile.append(row)
        else:
            rec_only.append(row)
    return rec_only, profile
