"""CLI: python -m app.rag.eval --golden path/to/golden.jsonl [--output results.csv] [--rerank path/to/rerank_scores.jsonl]"""
import argparse
from typing import List, Optional

from app.rag.eval.runner import run_eval_three_way


def main():
    parser = argparse.ArgumentParser(description="RAG 4-way eval: baseline / enhanced_reranker / current / current_reranker (RRF Top30 후보, Reranker 상위 20 pool → Top4)")
    parser.add_argument("--golden", required=True, help="Path to golden JSONL")
    parser.add_argument("--output", default=None, help="Output CSV path")
    parser.add_argument("--rerank", default=None, help="Path to rerank_scores.jsonl (optional)")
    parser.add_argument("--max-queries", type=int, default=None, help="앞에서 N개 질의만 평가 (부분 평가)")
    parser.add_argument("--verbose", "-v", action="store_true", help="질의별 검색 결과(Top4) 출력")
    parser.add_argument(
        "--pipelines",
        default=None,
        help="쉼표 구분 파이프라인 (예: baseline,enhanced_reranker,enhanced_reranker_no_contrastive,bm25_only,vector_only,contrastive_only). enhanced_reranker_no_contrastive=BM25+dense만 RRF(contrastive 제외). 미지정 시 기본 4-way",
    )
    parser.add_argument(
        "--no-rerank",
        action="store_true",
        help="enhanced_reranker 등에서 HF 리랭커 API를 호출하지 않음(RRF만, 인프라 500 시 재현 가능한 지표용)",
    )
    args = parser.parse_args()
    pipelines: Optional[List[str]] = None
    if args.pipelines:
        pipelines = [p.strip() for p in args.pipelines.split(",") if p.strip()]
    run_eval_three_way(
        args.golden,
        output_csv=args.output,
        rerank_scores_path=args.rerank,
        verbose=args.verbose,
        max_queries=args.max_queries,
        pipelines=pipelines,
        use_reranker=not args.no_rerank,
        force_reranker=not args.no_rerank,
    )


if __name__ == "__main__":
    main()
