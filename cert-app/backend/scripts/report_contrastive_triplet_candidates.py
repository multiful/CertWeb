"""
Contrastive triplet 데이터셋 생성을 위한 positive / hard negative 후보 리포트.

골든셋(reco)을 로드해 질의별로:
- positive: gold_chunk_ids(또는 expected_certs)에 해당하는 자격증(qual_id → qual_name)
- hard_negative: 같은 main_field/ncs_large 내 다른 자격증 등 (app/rag/contrastive/hard_negative 규칙)

출력: 콘솔 테이블 + 선택적으로 JSONL (query, positive_cert_names, hard_negative_qual_ids, hard_negative_cert_names).

실행:
  uv run python scripts/report_contrastive_triplet_candidates.py --golden data/reco_golden_recommendation_18.jsonl
  uv run python scripts/report_contrastive_triplet_candidates.py --golden data/reco_golden_recommendation_18.jsonl --output data/contrastive_triplet_candidates.jsonl
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database import SessionLocal
from app.rag.eval.golden import load_golden
from app.rag.eval.common import normalize_gold_labels
from app.rag.eval.retrieval_metrics import _chunk_id_to_qual_id
from app.rag.contrastive.hard_negative import get_qual_fields_map, select_hard_negatives


def _qual_id_to_name_map(db):
    from sqlalchemy import text
    rows = db.execute(text("SELECT qual_id, qual_name FROM qualification WHERE is_active = TRUE")).fetchall()
    return {r.qual_id: (r.qual_name or "").strip() for r in rows}


def main():
    p = argparse.ArgumentParser(description="Contrastive triplet용 positive / hard negative 후보 리포트")
    p.add_argument("--golden", required=True, help="골든셋 JSONL (reco 형식)")
    p.add_argument("--output", default=None, help="출력 JSONL 경로 (선택)")
    p.add_argument("--max-hard", type=int, default=5, help="질의당 hard negative 최대 개수")
    args = p.parse_args()

    golden_path = Path(args.golden)
    if not golden_path.exists():
        print(f"파일 없음: {golden_path}")
        return 1

    golden = load_golden(str(golden_path))
    db = SessionLocal()
    try:
        golden = normalize_gold_labels(golden, db, drop_empty_gold=True)
    finally:
        db.close()

    qual_fields = get_qual_fields_map(db)
    all_qual_ids = list(qual_fields.keys())
    id2name = _qual_id_to_name_map(db)

    rows_out = []
    db = SessionLocal()
    try:
        for row in golden:
            q = (row.get("query_text") or row.get("question") or "").strip()
            gold_ids = set(row.get("gold_chunk_ids") or [])
            if not gold_ids:
                continue
            positive_qual_ids = []
            for cid in gold_ids:
                qid = _chunk_id_to_qual_id(cid)
                if qid is not None and qid not in positive_qual_ids:
                    positive_qual_ids.append(qid)
            if not positive_qual_ids:
                continue
            hard_neg_ids = select_hard_negatives(
                db, positive_qual_ids, all_qual_ids, qual_fields, max_per_sample=args.max_hard
            )
            pos_names = [id2name.get(qid, f"qual_id:{qid}") for qid in positive_qual_ids if id2name.get(qid)]
            hard_names = [id2name.get(qid, f"qual_id:{qid}") for qid in hard_neg_ids if id2name.get(qid)]
            rec = {
                "query": q,
                "positive_qual_ids": positive_qual_ids,
                "positive_cert_names": pos_names,
                "hard_negative_qual_ids": hard_neg_ids,
                "hard_negative_cert_names": hard_names,
            }
            rows_out.append(rec)
    finally:
        db.close()

    # 콘솔 테이블
    print("\n" + "=" * 100)
    print("[ Contrastive triplet 후보 ] positive = 골든 정답 자격증, hard_negative = 동일 분야 내 다른 자격증 후보")
    print("=" * 100)
    print(f"  {'Query (일부)':<42} | {'Positive':<28} | {'Hard negative (예시)'}")
    print("-" * 100)
    for r in rows_out:
        q_short = (r["query"][:40] + "..") if len(r["query"]) > 42 else r["query"]
        pos_str = ", ".join(r["positive_cert_names"][:3])
        if len(r["positive_cert_names"]) > 3:
            pos_str += f" (+{len(r['positive_cert_names'])-3})"
        hard_str = ", ".join(r["hard_negative_cert_names"][:4])
        if len(r["hard_negative_cert_names"]) > 4:
            hard_str += " ..."
        print(f"  {q_short:<42} | {pos_str:<28} | {hard_str}")
    print("=" * 100)
    print(f"  총 {len(rows_out)}건. contrastive 학습 시 query / positive_qual_ids / hard_negative_qual_ids triplet으로 사용.")

    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            for rec in rows_out:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        print(f"\n  저장: {out_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
