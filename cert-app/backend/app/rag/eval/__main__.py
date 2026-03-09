"""CLI: python -m app.rag.eval --golden path/to/golden.jsonl [--output results.csv] [--rerank path/to/rerank_scores.jsonl]"""
import argparse
from app.rag.eval.runner import run_eval_three_way


def main():
    parser = argparse.ArgumentParser(description="RAG 4-way eval: baseline / enhanced_reranker / current / current_reranker (RRF Top30 후보, Reranker 상위 20 pool → Top4)")
    parser.add_argument("--golden", required=True, help="Path to golden JSONL")
    parser.add_argument("--output", default=None, help="Output CSV path")
    parser.add_argument("--rerank", default=None, help="Path to rerank_scores.jsonl (optional)")
    parser.add_argument("--max-queries", type=int, default=None, help="앞에서 N개 질의만 평가 (부분 평가)")
    parser.add_argument("--verbose", "-v", action="store_true", help="질의별 검색 결과(Top4) 출력")
    args = parser.parse_args()
    run_eval_three_way(
        args.golden,
        output_csv=args.output,
        rerank_scores_path=args.rerank,
        verbose=args.verbose,
        max_queries=args.max_queries,
    )


if __name__ == "__main__":
    main()
