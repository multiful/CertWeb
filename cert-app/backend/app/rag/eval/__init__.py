from app.rag.eval.golden import load_golden
from app.rag.eval.retrieval_metrics import recall_at_k, precision_at_k, mrr, recall_at_k_qual, mrr_qual
from app.rag.eval.generation_metrics import citation_coverage, hallucination_proxy
# run_eval_three_way는 runner에서 직접 import (순환 임포트 방지: hybrid → query_type → eval → runner → hybrid)
from app.rag.eval.common import (
    normalize_gold_labels,
    compute_recall_hit_mrr,
    group_metrics_by_query_type,
    aggregate_metrics_over_queries,
    is_profile_golden,
    is_recommendation_golden,
    split_golden_by_benchmark,
)

__all__ = [
    "load_golden",
    "recall_at_k",
    "precision_at_k",
    "mrr",
    "recall_at_k_qual",
    "mrr_qual",
    "citation_coverage",
    "hallucination_proxy",
    "normalize_gold_labels",
    "compute_recall_hit_mrr",
    "group_metrics_by_query_type",
    "aggregate_metrics_over_queries",
    "is_profile_golden",
    "is_recommendation_golden",
    "split_golden_by_benchmark",
]
