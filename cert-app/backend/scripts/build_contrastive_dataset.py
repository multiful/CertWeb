"""
Contrastive 학습용 데이터셋 생성: reco golden JSONL → query / positive_qual_ids / hard_negative_qual_ids.
출력: JSONL (한 줄당 ContrastiveSample 형식) 및 선택적 triplet JSONL.

실행 (cert-app/backend에서):
  uv run python scripts/build_contrastive_dataset.py --golden path/to/reco_golden.jsonl --out data/contrastive_train.jsonl
  uv run python scripts/build_contrastive_dataset.py --golden path/to/reco_golden.jsonl --out data/contrastive_train.jsonl --triplet-out data/contrastive_triplets.jsonl

포맷:
- contrastive_train.jsonl: {"query", "positive_qual_ids", "hard_negative_qual_ids", "sample_id", "query_slots"}
- contrastive_triplets.jsonl: {"query", "positive_qual_id", "negative_qual_id", "sample_id"}
"""
import argparse
import json
import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pathlib import Path

from sqlalchemy import text

from app.database import SessionLocal
from app.rag.contrastive.schema import ContrastiveSample, contrastive_sample_to_triplets
from app.rag.contrastive.hard_negative import get_qual_fields_map, select_hard_negatives
from app.rag.eval.reco_golden import cert_names_to_gold_chunk_ids, _qual_id_to_name_map

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def load_reco_golden(path: str) -> list[dict]:
    """JSONL 로드. query_text, gold_ranked 필드 기대."""
    out = []
    p = Path(path)
    if not p.exists():
        return out
    with open(p, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return out


def main():
    parser = argparse.ArgumentParser(description="Build contrastive dataset from reco golden JSONL")
    parser.add_argument("--golden", required=True, help="Path to reco golden JSONL (query_text, gold_ranked)")
    parser.add_argument("--out", default="data/contrastive_train.jsonl", help="Output JSONL path (samples)")
    parser.add_argument("--triplet-out", default="", help="Optional: output triplet JSONL path")
    parser.add_argument("--max-hard-negatives", type=int, default=5, help="Max hard negatives per sample")
    args = parser.parse_args()

    golden = load_reco_golden(args.golden)
    if not golden:
        logger.warning("No rows in golden file %s", args.golden)
        return

    db = SessionLocal()
    try:
        qual_id_to_name = _qual_id_to_name_map(db)
        qual_fields = get_qual_fields_map(db)
        all_qual_ids = list(qual_fields.keys())

        samples: list[ContrastiveSample] = []
        for i, row in enumerate(golden):
            query = (row.get("query_text") or row.get("question") or "").strip()
            if not query:
                continue
            gold_ranked = row.get("gold_ranked") or []
            chunk_ids = cert_names_to_gold_chunk_ids(db, gold_ranked, min_relevance=1, qual_id_to_name=qual_id_to_name)
            positive_qual_ids = []
            for cid in chunk_ids:
                if ":" in cid:
                    try:
                        qid = int(cid.split(":")[0])
                        positive_qual_ids.append(qid)
                    except ValueError:
                        pass
            positive_qual_ids = list(dict.fromkeys(positive_qual_ids))
            if not positive_qual_ids:
                continue
            hard_negative_qual_ids = select_hard_negatives(
                db, positive_qual_ids, all_qual_ids, qual_fields, max_per_sample=args.max_hard_negatives
            )
            if not hard_negative_qual_ids:
                continue
            samples.append(
                ContrastiveSample(
                    query=query,
                    positive_qual_ids=positive_qual_ids,
                    hard_negative_qual_ids=hard_negative_qual_ids,
                    sample_id=row.get("id") or str(i),
                )
            )
    finally:
        db.close()

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        for s in samples:
            f.write(json.dumps(s.to_dict(), ensure_ascii=False) + "\n")
    logger.info("Wrote %s samples to %s", len(samples), out_path)

    if args.triplet_out:
        triplets = []
        for s in samples:
            triplets.extend(contrastive_sample_to_triplets(s))
        trip_path = Path(args.triplet_out)
        trip_path.parent.mkdir(parents=True, exist_ok=True)
        with open(trip_path, "w", encoding="utf-8") as f:
            for t in triplets:
                f.write(json.dumps(t.to_dict(), ensure_ascii=False) + "\n")
        logger.info("Wrote %s triplets to %s", len(triplets), trip_path)


if __name__ == "__main__":
    main()
