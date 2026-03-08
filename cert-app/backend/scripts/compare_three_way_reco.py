"""
추천 API 3-way 비교: 현재 GitHub 스타일 vs 로컬 수정 vs 고도화 RAG(hybrid_retrieve).
동일 골든(reco_golden_recommendation_18.jsonl)으로 세 경로를 평가해 요약 테이블 출력.

실행 (cert-app/backend):
  uv run python scripts/compare_three_way_reco.py --golden data/reco_golden_recommendation_18.jsonl
  uv run python scripts/compare_three_way_reco.py --golden data/reco_golden_recommendation_18.jsonl --out data/compare_three_way.json
"""
import argparse
import json
import os
import sys
import time
from pathlib import Path

_backend = Path(__file__).resolve().parents[1]
if str(_backend) not in sys.path:
    sys.path.insert(0, str(_backend))

from fastapi.testclient import TestClient

from app.database import SessionLocal, get_db
from app.rag.eval.golden import load_golden
from app.rag.eval.common import normalize_gold_labels, compute_recall_hit_mrr
from app.api.deps import check_rate_limit, get_optional_user
from main import app


def _override_deps():
    def override_get_db():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    def noop_optional_user():
        return None

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[check_rate_limit] = lambda: None
    app.dependency_overrides[get_optional_user] = noop_optional_user


def run_recommendation_api_eval(
    golden: list,
    client: TestClient,
    limit: int = 15,
    use_github_rrf: bool = False,
    collect_per_query: bool = False,
):
    if use_github_rrf:
        os.environ["RECOMMENDATION_USE_GITHUB_RRF"] = "1"
    else:
        os.environ.pop("RECOMMENDATION_USE_GITHUB_RRF", None)
    n = 0
    r5 = r10 = r15 = r20 = hit15 = s15 = mrr15 = 0.0
    latencies = []
    per_query_rows = [] if collect_per_query else None
    for row in golden:
        major = (row.get("major") or "").strip()
        query_text = (row.get("query_text") or row.get("question") or "").strip()
        gold_ids = set(row.get("gold_chunk_ids") or [])
        if not major or not gold_ids:
            continue
        interest = query_text if query_text != major else None
        start = time.perf_counter()
        try:
            resp = client.get(
                "/api/v1/recommendations/ai/hybrid-recommendation",
                params={"major": major, "interest": interest, "limit": limit},
                headers={"Host": "localhost"},
            )
        except Exception:
            n += 1
            continue
        lat_ms = (time.perf_counter() - start) * 1000
        if resp.status_code != 200:
            n += 1
            continue
        data = resp.json()
        results = data.get("results") or []
        retrieved = [f"{r.get('qual_id')}:0" for r in results if r.get("qual_id") is not None]
        m = compute_recall_hit_mrr(retrieved, gold_ids, k_recall=[5, 10, 15, 20], k_top=15)
        r5 += m.get("Recall@5", 0)
        r10 += m.get("Recall@10", 0)
        r15 += m.get("Recall@15", 0)
        r20 += m.get("Recall@20", 0)
        hit15 += m.get("Hit@15", 0)
        s15 += m.get("Success@15", 0)
        mrr15 += m.get("MRR@4", 0)
        latencies.append(lat_ms)
        if collect_per_query:
            per_query_rows.append({
                "major": major,
                "interest": interest,
                "gold_chunk_ids": list(gold_ids),
                "retrieved": [r.get("qual_id") for r in results[:limit] if r.get("qual_id") is not None],
                "qual_names": [r.get("qual_name", "") for r in results[:limit]],
            })
        n += 1
    if n == 0:
        return None, (per_query_rows or [])
    return {
        "n": n,
        "Recall@5": r5 / n, "Recall@10": r10 / n, "Recall@15": r15 / n, "Recall@20": r20 / n,
        "Hit@15": hit15 / n, "Success@15": s15 / n, "MRR@15": mrr15 / n,
        "Avg_Latency_ms": sum(latencies) / len(latencies) if latencies else 0,
    }, (per_query_rows or [])


def run_rag_hybrid_eval(golden: list, max_queries: int = 100, collect_per_query: bool = False):
    from app.rag.retrieve.hybrid import hybrid_retrieve
    db = SessionLocal()
    per_query_rows = [] if collect_per_query else None
    try:
        n = 0
        r5 = r10 = r20 = hit20 = s4 = mrr4 = 0.0
        latencies = []
        for row in golden[:max_queries]:
            q = (row.get("question") or row.get("query_text") or "").strip()
            gold_ids = set(row.get("gold_chunk_ids") or [])
            if not q or not gold_ids:
                continue
            start = time.perf_counter()
            results = hybrid_retrieve(db, q, top_k=20, use_reranker=False)
            lat_ms = (time.perf_counter() - start) * 1000
            retrieved = [c[0] for c in results]
            m = compute_recall_hit_mrr(retrieved, gold_ids, k_recall=[5, 10, 20], k_top=4)
            r5 += m.get("Recall@5", 0)
            r10 += m.get("Recall@10", 0)
            r20 += m.get("Recall@20", 0)
            hit20 += m.get("Hit@20", 0)
            s4 += m.get("Success@4", 0)
            mrr4 += m.get("MRR@4", 0)
            latencies.append(lat_ms)
            if collect_per_query:
                per_query_rows.append({
                    "query": q,
                    "gold_chunk_ids": list(gold_ids),
                    "retrieved_chunk_ids": retrieved[:20],
                })
            n += 1
        if n == 0:
            return None, (per_query_rows or [])
        return {
            "n": n,
            "Recall@5": r5 / n, "Recall@10": r10 / n, "Recall@20": r20 / n,
            "Hit@20": hit20 / n, "Success@4": s4 / n, "MRR@4": mrr4 / n,
            "Avg_Latency_ms": sum(latencies) / len(latencies) if latencies else 0,
        }, (per_query_rows or [])
    finally:
        db.close()


def main():
    p = argparse.ArgumentParser(description="3-way: GitHub 추천 API vs 로컬 수정 추천 API vs 고도화 RAG")
    p.add_argument("--golden", required=True, help="reco 골든 JSONL")
    p.add_argument("--max-queries", type=int, default=100)
    p.add_argument("--out", default=None, help="결과 JSON 저장 경로")
    p.add_argument("--per-query", action="store_true", help="질의별 상위 결과 리스트 출력 (stdout 또는 --out 디렉터리)")
    args = p.parse_args()

    golden_path = Path(args.golden)
    if not golden_path.exists():
        print(f"파일 없음: {golden_path}")
        return 1

    golden = load_golden(str(golden_path))
    db = SessionLocal()
    try:
        golden = normalize_gold_labels(golden, db, drop_empty_gold=True)
        golden = golden[: args.max_queries]
    finally:
        db.close()
    if not golden:
        print("골든셋 비어 있음")
        return 1

    _override_deps()
    client = TestClient(app)

    collect_pq = args.per_query
    # 1) 현재 GitHub 스타일 (단순 RRF, 동의어 없음)
    print("평가 중: 현재 GitHub 추천 API (단순 RRF)...")
    github_metrics, github_pq = run_recommendation_api_eval(
        golden, client, use_github_rrf=True, collect_per_query=collect_pq
    )
    os.environ.pop("RECOMMENDATION_USE_GITHUB_RRF", None)

    # 2) 로컬 수정 (가중치 RRF + 동의어 확장)
    print("평가 중: 로컬 수정 추천 API (가중치 RRF + 동의어)...")
    local_metrics, local_pq = run_recommendation_api_eval(
        golden, client, use_github_rrf=False, collect_per_query=collect_pq
    )

    # 3) 고도화 RAG (BM25+Vector+RRF, hybrid_retrieve)
    print("평가 중: 고도화 RAG (hybrid_retrieve)...")
    rag_metrics, rag_pq = run_rag_hybrid_eval(
        golden, max_queries=args.max_queries, collect_per_query=collect_pq
    )

    out = {
        "golden": str(golden_path),
        "n_queries": len([r for r in golden if (r.get("gold_chunk_ids") or []) and (r.get("major") or r.get("query_text"))]),
        "github_recommendation_api": github_metrics,
        "local_recommendation_api": local_metrics,
        "enhanced_rag_hybrid": rag_metrics,
    }
    if collect_pq and (github_pq or local_pq or rag_pq):
        out["per_query"] = {
            "github_api": github_pq or [],
            "local_api": local_pq or [],
            "enhanced_rag": rag_pq or [],
        }
    if args.out:
        with open(Path(args.out), "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False, indent=2)
        print(f"\n결과 저장: {args.out}")
    if collect_pq and (github_pq or local_pq or rag_pq):
        print("\n[ 질의별 결과 리스트 ]")
        for i in range(max(len(github_pq or []), len(local_pq or []), len(rag_pq or []))):
            g = (github_pq or [])[i] if i < len(github_pq or []) else {}
            l = (local_pq or [])[i] if i < len(local_pq or []) else {}
            r = (rag_pq or [])[i] if i < len(rag_pq or []) else {}
            q_label = g.get("major", "") or l.get("major", "") or r.get("query", "")
            print(f"\n--- Query {i+1}: {q_label[:60]} ---")
            print("  Gold:", (g.get("gold_chunk_ids") or l.get("gold_chunk_ids") or r.get("gold_chunk_ids") or [])[:10])
            print("  GitHub API (qual_id):", (g.get("retrieved") or [])[:10])
            print("  Local API (qual_id):", (l.get("retrieved") or [])[:10])
            print("  RAG (chunk_id):", (r.get("retrieved_chunk_ids") or [])[:10])

    # 요약 테이블
    print("\n" + "=" * 90)
    print("[ 3-way 비교 ] 동일 골든: " + golden_path.name)
    print("=" * 90)
    print(f"{'경로':<32} {'R@5':>8} {'R@15/R@20':>10} {'Hit@15/20':>10} {'MRR@15/4':>10} {'Lat(ms)':>10}")
    print("-" * 90)
    for label, m in [
        ("현재 GitHub (추천 API)", github_metrics),
        ("로컬 수정 (추천 API)", local_metrics),
        ("고도화 RAG (hybrid)", rag_metrics),
    ]:
        if m is None:
            print(f"  {label:<30} (오류 또는 데이터 없음)")
            continue
        r5 = m.get("Recall@5", 0)
        r15 = m.get("Recall@15") or m.get("Recall@20") or 0
        hit = m.get("Hit@15") or m.get("Hit@20") or 0
        mrr = m.get("MRR@15") or m.get("MRR@4") or 0
        lat = m.get("Avg_Latency_ms", 0)
        print(f"  {label:<30} {r5:>8.4f} {r15:>10.4f} {hit:>10.2f} {mrr:>10.4f} {lat:>10.1f}")
    print("=" * 90)
    return 0


if __name__ == "__main__":
    sys.exit(main())
