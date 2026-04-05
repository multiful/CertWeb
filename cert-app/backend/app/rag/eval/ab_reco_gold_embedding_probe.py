"""
reco 골든(예: reco_golden_recommendation_*_clean.jsonl) 앞 N줄에 대해,
질의 임베딩과 정답 자격증 문서 임베딩의 코사인 유사도를
현재 인덱싱 문자열(A) vs 변형 문자열(B)로 비교하는 경량 A/B 프로브.

목적
----
- DB `qualification`에는 현재 `ncs_large` 한 컬럼만 있고, UI/코퍼스에선 도메인형 라벨이
  섞여 있을 수 있음. 정식 NCS 대·중 직무 코드/명칭을 문서에 추가하면
  밀집 벡터가 질의에 더 맞아질지(또는 길이·중복으로 희석될지) 1차 스크리닝.

한계
----
- hybrid RAG 전체( BM25 · dense · contrastive · 메타 소프트 · 리랭커 )를 재현하지 않음.
  "질의 ↔ 정답 자격증 본문" 코사인만 측정한다.
- 실제 서비스 지표(MRR·Recall@K) A/B는 `certificates_vectors` 재임베딩·BM25 재빌드가 필요하다.
  다만 골든에 등장하는 qual_id만 부분 재인덱싱하면 비용을 줄일 수 있다.

실행 예
-------
  cd cert-app/backend
  set PYTHONPATH=...
  python -m app.rag.eval.ab_reco_gold_embedding_probe \\
    --golden dataset/reco_golden_recommendation_19_clean.jsonl \\
    --max-queries 20 --variant structured_extra
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from typing import Any, Dict, List, Sequence, Tuple

from sqlalchemy import text

from app.database import SessionLocal
from app.rag.eval.common import build_reco_eval_rag_query, normalize_gold_labels
from app.rag.eval.golden import load_golden
from app.rag.ingest.chunker import build_content_from_row
from app.utils.ai import get_embedding


def _cos(u: Sequence[float], v: Sequence[float]) -> float:
    if not u or not v or len(u) != len(v):
        return 0.0
    dot = sum(a * b for a, b in zip(u, v))
    na = math.sqrt(sum(a * a for a in u))
    nb = math.sqrt(sum(b * b for b in v))
    if na <= 0 or nb <= 0:
        return 0.0
    return dot / (na * nb)


def _fetch_qual_rows(db, qual_ids: List[int]) -> Dict[int, Dict[str, Any]]:
    if not qual_ids:
        return {}
    rows = db.execute(
        text(
            """
            SELECT qual_id, qual_name, qual_type, main_field, ncs_large,
                   managing_body, grade_code
            FROM qualification
            WHERE qual_id = ANY(:ids)
            """
        ),
        {"ids": qual_ids},
    ).mappings()
    return {int(r["qual_id"]): dict(r) for r in rows}


def _variant_b(
    mode: str,
    text_a: str,
    row: Dict[str, Any],
    custom_suffix: str,
) -> str:
    if mode == "duplicate":
        return f"{text_a} | {text_a}"
    if mode == "structured_extra":
        mf = (row.get("main_field") or "").strip()
        ncs = (row.get("ncs_large") or "").strip()
        # 정식 NCS 코드가 아직 없을 때: '라벨을 한 번 더 구조화해 넣는' 스트레스 테스트
        return (
            f"{text_a} | 직무대분류(세분): {ncs} | 직무중분류(세분): {mf} "
            f"| 도메인요약: {ncs} / {mf}"
        )
    if mode == "custom":
        suf = (custom_suffix or "").strip()
        return f"{text_a} | {suf}" if suf else text_a
    raise ValueError(f"unknown variant: {mode}")


def main(argv: List[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="reco 골든 N개: 질의↔정답 문서 임베딩 A/B 프로브")
    p.add_argument("--golden", required=True, help="reco 형식 JSONL 경로")
    p.add_argument("--max-queries", type=int, default=20, help="앞에서 N개 질의만")
    p.add_argument(
        "--variant",
        choices=["duplicate", "structured_extra", "custom"],
        default="structured_extra",
        help="B 문서: duplicate=전문 복붙(강한 노이즈), structured_extra=대·중·도메인 라벨 덧붙임, custom=--custom-suffix",
    )
    p.add_argument("--custom-suffix", default="", help="variant=custom 일 때 문서 끝에 붙일 문자열")
    p.add_argument("--json", action="store_true", help="요약만 JSON 한 줄로 출력")
    args = p.parse_args(argv)

    golden = load_golden(args.golden)
    if not golden:
        print("골든이 비었습니다.", file=sys.stderr)
        return 1
    if args.max_queries and args.max_queries > 0:
        golden = golden[: args.max_queries]

    db = SessionLocal()
    try:
        golden = normalize_gold_labels(golden, db, drop_empty_gold=True)
    finally:
        db.close()

    if not golden:
        print("정규화 후 유효 행이 없습니다.", file=sys.stderr)
        return 1

    db = SessionLocal()
    deltas: List[float] = []
    sim_as: List[float] = []
    sim_bs: List[float] = []
    per_row: List[Dict[str, Any]] = []

    try:
        for row in golden:
            q_raw = (row.get("question") or row.get("query_text") or "").strip()
            q = build_reco_eval_rag_query(row) if (row.get("major") or "").strip() else q_raw
            gold_ids = row.get("gold_chunk_ids") or []
            qual_ids: List[int] = []
            for cid in gold_ids:
                if cid and ":" in str(cid):
                    try:
                        qual_ids.append(int(str(cid).split(":")[0]))
                    except ValueError:
                        pass
            if not q or not qual_ids:
                continue

            q_vec = get_embedding(q)
            rows_by_id = _fetch_qual_rows(db, qual_ids)

            row_deltas: List[float] = []
            for qid in qual_ids:
                rdb = rows_by_id.get(qid)
                if not rdb:
                    continue
                text_a = build_content_from_row(rdb)
                text_b = _variant_b(args.variant, text_a, rdb, args.custom_suffix)
                a_vec = get_embedding(text_a)
                b_vec = get_embedding(text_b)
                sa = _cos(q_vec, a_vec)
                sb = _cos(q_vec, b_vec)
                sim_as.append(sa)
                sim_bs.append(sb)
                d = sb - sa
                deltas.append(d)
                row_deltas.append(d)

            if row_deltas:
                per_row.append(
                    {
                        "query_preview": q[:80],
                        "n_gold": len(row_deltas),
                        "mean_delta": sum(row_deltas) / len(row_deltas),
                    }
                )
    finally:
        db.close()

    n = len(deltas)
    if n == 0:
        print("측정할 (질의, 정답 자격증) 쌍이 없습니다.", file=sys.stderr)
        return 1

    mean_a = sum(sim_as) / n
    mean_b = sum(sim_bs) / n
    mean_d = sum(deltas) / n
    win = sum(1 for d in deltas if d > 1e-6)
    lose = sum(1 for d in deltas if d < -1e-6)
    tie = n - win - lose

    summary = {
        "golden": args.golden,
        "max_queries": args.max_queries,
        "variant_b": args.variant,
        "pairs": n,
        "mean_cosine_a": round(mean_a, 6),
        "mean_cosine_b": round(mean_b, 6),
        "mean_delta_b_minus_a": round(mean_d, 6),
        "b_better_count": win,
        "b_worse_count": lose,
        "tie_count": tie,
    }

    if args.json:
        print(json.dumps(summary, ensure_ascii=False))
        return 0

    print("=== reco 골든 임베딩 프로브 (질의 ↔ 정답 자격증 문서) ===")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print("\n--- 질의별 평균 delta (B-A) ---")
    for i, pr in enumerate(per_row[:25], 1):
        print(f"{i}. delta={pr['mean_delta']:.6f} golds={pr['n_gold']} | {pr['query_preview']!r}")
    if len(per_row) > 25:
        print(f"... 외 {len(per_row) - 25}개 질의")
    print(
        "\n해석: delta>0 이면 B 문구가 질의와의 코사인을 평균적으로 올린 것."
        " 전체 추천 품질과는 별개이며, 확정은 재인덱싱 후 python -m app.rag.eval 로 검증 권장."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
