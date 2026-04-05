"""
골든셋으로 파이프라인별 latency 분포·분산 측정 (리랭커 제외 권장).

- 워밍업 패스: cold-start·캐시 워밍을 측정에서 제외
- 여러 패스: 질의×패스 풀드 샘플로 mean±stdev·p50·p95, 패스 평균의 패스 간 σ
- enhanced_reranker 포함 시 hybrid 내부 구간(pre_parallel / parallel / fusion_ranking) 집계

실행 예:
  cd cert-app/backend && set PYTHONPATH=. && python -m app.rag.eval.latency_bench \\
    --golden dataset/reco_golden_recommendation_19_clean.jsonl --max-queries 20 --passes 5 --warmup 1
"""
from __future__ import annotations

import argparse
import json
import math
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional

from app.rag.eval.runner import run_eval_three_way


def _mean(xs: List[float]) -> float:
    return sum(xs) / len(xs) if xs else 0.0


def _stdev(xs: List[float]) -> float:
    if len(xs) < 2:
        return 0.0
    m = _mean(xs)
    return math.sqrt(sum((x - m) ** 2 for x in xs) / (len(xs) - 1))


def _pctl(xs: List[float], p: float) -> float:
    if not xs:
        return 0.0
    s = sorted(xs)
    i = min(max(int(math.ceil(p * len(s))) - 1, 0), len(s) - 1)
    return s[i]


def summarize_latencies(samples: List[float]) -> Dict[str, float]:
    return {
        "n": float(len(samples)),
        "mean": _mean(samples),
        "stdev": _stdev(samples),
        "p50": _pctl(samples, 0.50),
        "p95": _pctl(samples, 0.95),
        "min": min(samples) if samples else 0.0,
        "max": max(samples) if samples else 0.0,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="RAG 골든셋 반복 패스로 파이프라인별 latency 통계 (Cross-Encoder 끔)"
    )
    parser.add_argument("--golden", required=True, help="골든 JSONL 경로")
    parser.add_argument("--max-queries", type=int, default=None)
    parser.add_argument(
        "--pipelines",
        default="baseline,current,enhanced_reranker,enhanced_reranker_no_contrastive",
        help="쉼표 구분 파이프라인명",
    )
    parser.add_argument("--passes", type=int, default=3, help="측정에 사용할 패스 수")
    parser.add_argument("--warmup", type=int, default=1, help="버릴 워밍업 패스 수")
    parser.add_argument("--json-out", type=str, default=None, help="전체 리포트 JSON")
    args = parser.parse_args()
    pipes = [x.strip() for x in args.pipelines.split(",") if x.strip()]

    pooled: Dict[str, List[float]] = defaultdict(list)
    pass_avg_by_pipe: Dict[str, List[float]] = defaultdict(list)
    phase_keys: Dict[str, List[float]] = defaultdict(list)
    last_metrics: Optional[Dict] = None

    total_rounds = args.warmup + args.passes
    phase_collector: Optional[List[Dict[str, float]]] = [] if "enhanced_reranker" in pipes else None

    for i in range(total_rounds):
        lat_dump: Dict[str, List[float]] = {}
        last_metrics = run_eval_three_way(
            args.golden,
            max_queries=args.max_queries,
            pipelines=pipes,
            use_reranker=False,
            force_reranker=False,
            quiet=True,
            latency_samples_by_pipeline=lat_dump,
            enhanced_hybrid_phase_rows=phase_collector,
        )
        if i < args.warmup:
            if phase_collector is not None:
                phase_collector.clear()
            continue
        for name, xs in lat_dump.items():
            pooled[name].extend(xs)
            pass_avg_by_pipe[name].append(_mean(xs))
        if phase_collector is not None:
            for row in phase_collector:
                for k, v in row.items():
                    phase_keys[k].append(float(v))
            phase_collector.clear()

    report: Dict = {
        "golden": str(Path(args.golden).resolve()),
        "max_queries": args.max_queries,
        "pipelines": pipes,
        "warmup_passes": args.warmup,
        "measured_passes": args.passes,
        "reranker": False,
        "pooled_latency_ms": {n: summarize_latencies(pooled[n]) for n in pooled},
        "pass_mean_latency_ms": {
            n: {
                "mean_of_pass_avgs": _mean(pass_avg_by_pipe[n]),
                "stdev_across_passes": _stdev(pass_avg_by_pipe[n]),
                "pass_avgs": list(pass_avg_by_pipe[n]),
            }
            for n in pass_avg_by_pipe
        },
        "enhanced_hybrid_phases_ms": {k: summarize_latencies(v) for k, v in phase_keys.items()},
        "metrics_last_pass": last_metrics,
    }

    print("\n[ RAG latency bench — Cross-Encoder OFF, pooled over passes ]")
    print("-" * 72)
    for name in pipes:
        if name not in pooled:
            continue
        s = summarize_latencies(pooled[name])
        pa = pass_avg_by_pipe.get(name, [])
        print(
            f"  {name}: n={int(s['n'])} mean={s['mean']:.1f}±{s['stdev']:.1f}ms "
            f"p50={s['p50']:.0f} p95={s['p95']:.0f} | "
            f"pass_avg_mean={_mean(pa):.1f} pass_avg_stdev={_stdev(pa):.1f}"
        )
    if phase_keys:
        print("-" * 72)
        print("  enhanced_reranker hybrid phases (리랭커 제외, 질의 샘플 합산):")
        for k in sorted(phase_keys.keys()):
            s = summarize_latencies(phase_keys[k])
            print(f"    {k}: mean={s['mean']:.1f}ms p95={s['p95']:.0f} (n={int(s['n'])})")
    print("-" * 72)
    print(
        "  해석: pooled ±σ는 질의 간 편차 포함. pass_avg_stdev는 패스마다 계산한 평균 latency의 흔들림.\n"
        "  단일 패스 avg_ms만으로 A/B 하면 네트워크·캐시 노이즈에 취약함 — 본 벤치 권장."
    )

    if args.json_out:
        outp = Path(args.json_out)
        outp.parent.mkdir(parents=True, exist_ok=True)
        with open(outp, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        print(f"  JSON -> {outp}")


if __name__ == "__main__":
    main()
