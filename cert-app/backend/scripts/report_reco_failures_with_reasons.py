"""
실패 케이스 수집 + failure reason 자동 태깅.
Recall@20 < 1 또는 Top4 실패 질의에 대해 원인 후보 태그를 붙여 다음 액션을 빠르게 한다.

태그 정의:
- sparse_miss: BM25 top-20에 정답 없음
- dense_miss: Vector top-20에 정답 없음
- both_retrieved_but_low_rank: BM25·Vector 둘 다 top-20에 정답 있으나 최종 Top4에는 없음
- alias_missing: cert_name_included 유형 + sparse_miss (별칭 누락 의심)
- major_missing: major+job 유형 + 둘 다 miss (전공 매핑 부족 의심)
- purpose_mismatch: purpose_only 유형 + 실패 (목적 표현 매칭 부족 의심)
- roadmap_miss: roadmap 유형 + 실패 (순서/로드맵 회수 부족 의심)
- unrelated_high_score_intrusion: Top4에 정답 없고 비정답이 상위에 노출 (다른 cert가 고점으로 침입)

실행 (cert-app/backend):
  uv run python scripts/report_reco_failures_with_reasons.py --golden data/reco_golden_recommendation_18.jsonl
  uv run python scripts/report_reco_failures_with_reasons.py --golden data/reco_golden_recommendation_18.jsonl --out data/reco_failures_tagged.jsonl --reranker
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.database import SessionLocal
from app.rag.config import get_rag_index_dir, get_rag_settings
from app.rag.eval.golden import load_golden
from app.rag.eval.common import normalize_gold_labels
from app.rag.eval.query_type import classify_query_type
from app.rag.eval.retrieval_metrics import success_at_k
from app.rag.index.bm25_index import BM25Index
from app.rag.index.vector_index import get_vector_search
from app.rag.retrieve.hybrid import hybrid_retrieve
from app.rag.utils.query_processor import expand_query_single_string
from app.rag.utils.dense_query_rewrite import rewrite_for_dense

TOP_K = 20
TOP_K_FINAL = 4


def get_bm25_top_k(query: str, k: int):
    index_dir = get_rag_index_dir() / "bm25.pkl"
    if not Path(index_dir).exists():
        return []
    bm25 = BM25Index(index_path=Path(index_dir))
    bm25.load()
    bm25_query = expand_query_single_string(query, for_recommendation=True)
    return bm25.search(bm25_query, k=k)


def get_vector_top_k(db, query: str, k: int):
    settings = get_rag_settings()
    vector_query = query
    if getattr(settings, "RAG_DENSE_USE_QUERY_REWRITE", True):
        try:
            rewritten = rewrite_for_dense(query, profile=None)
            if rewritten and rewritten.strip():
                vector_query = rewritten
        except Exception:
            if getattr(settings, "RAG_DENSE_QUERY_REWRITE_FALLBACK", True):
                vector_query = query
    return get_vector_search(
        db, vector_query, top_k=k, threshold=settings.RAG_VECTOR_THRESHOLD, use_rewrite=False
    )


def tag_failure_reasons(
    query_type: str,
    bm25_ok: bool,
    vec_ok: bool,
    top4_ok: bool,
    top4_ids: list,
    gold_ids: set,
) -> list:
    """자동 태깅: 실패 원인 후보 리스트."""
    reasons = []
    if not bm25_ok:
        reasons.append("sparse_miss")
    if not vec_ok:
        reasons.append("dense_miss")
    if bm25_ok and vec_ok and not top4_ok:
        reasons.append("both_retrieved_but_low_rank")
    if query_type == "cert_name_included" and not bm25_ok:
        reasons.append("alias_missing")
    if query_type == "major+job" and not bm25_ok and not vec_ok:
        reasons.append("major_missing")
    if query_type == "purpose_only" and (not bm25_ok or not vec_ok or not top4_ok):
        reasons.append("purpose_mismatch")
    if query_type == "roadmap" and (not bm25_ok or not vec_ok or not top4_ok):
        reasons.append("roadmap_miss")
    if not top4_ok and top4_ids:
        non_gold_in_top4 = [cid for cid in top4_ids[:TOP_K_FINAL] if cid not in gold_ids]
        if non_gold_in_top4:
            reasons.append("unrelated_high_score_intrusion")
    return reasons


def run(golden_path: str, use_reranker: bool, max_queries: int | None, out_path: str | None) -> dict:
    golden = load_golden(golden_path)
    if not golden:
        return {"error": "empty golden", "n": 0}

    db = SessionLocal()
    try:
        golden = normalize_gold_labels(golden, db, drop_empty_gold=True)
    finally:
        db.close()

    if max_queries and max_queries > 0:
        golden = golden[:max_queries]

    bm25_available = Path(get_rag_index_dir() / "bm25.pkl").exists()
    failures = []
    db = SessionLocal()
    try:
        for i, row in enumerate(golden):
            q = (row.get("question") or row.get("query_text") or "").strip()
            gold_ids = set(row.get("gold_chunk_ids") or [])
            if not q or not gold_ids:
                continue

            qt = classify_query_type(q, row.get("query_type"))
            bm25_list = get_bm25_top_k(q, TOP_K) if bm25_available else []
            vec_list = get_vector_top_k(db, q, TOP_K)
            hybrid_list = hybrid_retrieve(db, q, top_k=TOP_K_FINAL, use_reranker=use_reranker)

            bm25_ids = [c[0] for c in bm25_list[:TOP_K]]
            vec_ids = [c[0] for c in vec_list[:TOP_K]]
            top4_ids = [c[0] for c in hybrid_list[:TOP_K_FINAL]]

            bm25_ok = success_at_k(bm25_ids, gold_ids, TOP_K) > 0
            vec_ok = success_at_k(vec_ids, gold_ids, TOP_K) > 0
            top4_ok = success_at_k(top4_ids, gold_ids, TOP_K_FINAL) > 0

            # Recall@20 equivalent: any hit in top-20 (use hybrid top-20 for consistency)
            hybrid_20 = hybrid_retrieve(db, q, top_k=TOP_K, use_reranker=False)
            hybrid_20_ids = [c[0] for c in hybrid_20[:TOP_K]]
            recall20_ok = success_at_k(hybrid_20_ids, gold_ids, TOP_K) > 0

            if recall20_ok and top4_ok:
                continue  # 성공 케이스 제외, 실패만 수집

            reasons = tag_failure_reasons(qt, bm25_ok, vec_ok, top4_ok, top4_ids, gold_ids)
            failures.append({
                "query_id": i,
                "query_text": q[:120] + ("..." if len(q) > 120 else ""),
                "query_type": qt,
                "gold_chunk_ids": list(gold_ids),
                "recall20_ok": recall20_ok,
                "top4_ok": top4_ok,
                "bm25_ok": bm25_ok,
                "vec_ok": vec_ok,
                "failure_reasons": reasons,
                "top4_retrieved": top4_ids,
            })
    finally:
        db.close()

    n_fail = len(failures)
    n_total = sum(1 for row in golden if (row.get("gold_chunk_ids") or []) and (row.get("question") or row.get("query_text")))
    print("\n" + "=" * 80)
    print("실패 케이스 수집 (failure reason 자동 태깅)")
    print("=" * 80)
    print(f"  Golden: {Path(golden_path).name}  total_queries={n_total}  failures={n_fail}")
    print("-" * 80)
    for f in failures:
        print(f"  [{f['query_id']}] {f['query_type']}  reasons={f['failure_reasons']}")
        print(f"      bm25_ok={f['bm25_ok']}  vec_ok={f['vec_ok']}  top4_ok={f['top4_ok']}")
    print("=" * 80)

    if out_path and failures:
        with open(out_path, "w", encoding="utf-8") as fp:
            for f in failures:
                fp.write(json.dumps(f, ensure_ascii=False) + "\n")
        print(f"  Out: {out_path}")

    return {"n_total": n_total, "n_failures": n_fail, "failures": failures}


def main():
    p = argparse.ArgumentParser(description="실패 케이스 수집 + failure reason 태깅")
    p.add_argument("--golden", required=True, help="골든셋 JSONL")
    p.add_argument("--out", default=None, help="출력 JSONL (실패 행만)")
    p.add_argument("--max-queries", type=int, default=None)
    p.add_argument("--reranker", action="store_true", help="Top4 평가 시 reranker 사용")
    args = p.parse_args()

    path = Path(args.golden)
    if not path.exists():
        print(f"파일 없음: {path}")
        return 1
    result = run(str(path), use_reranker=args.reranker, max_queries=args.max_queries, out_path=args.out)
    if result.get("error"):
        print(f"Error: {result['error']}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
