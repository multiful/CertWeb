"""
Contrastive 프로필 JSON 병합: 기존 골든셋 + 새로 생성한 JSON 배열을 합치고 query_id 재부여.

- base + new 결합 후 query_id를 p001 ~ p{N} 연속 부여.
- (선택) --dedup 시 (raw_query, positive 집합) 동일한 row는 1건만 유지 (negative 많은 쪽 우선).

실행 (cert-app/backend):
  uv run python scripts/merge_contrastive_profile_json.py --base data/contrastive_profile_train_example.json --new data/contrastive_profile_new.json --out data/contrastive_profile_train_example.json
  uv run python scripts/merge_contrastive_profile_json.py --base data/contrastive_profile_train_example.json --new data/contrastive_profile_new.json --out data/contrastive_merged.json --dedup
"""
import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path


def get_positive_qual_ids(item: dict) -> tuple:
    """positive 또는 positives에서 qual_id 집합을 정렬된 튜플로."""
    ids = []
    if "positives" in item and item["positives"]:
        for p in item["positives"]:
            qid = p.get("qual_id")
            if qid is not None:
                ids.append(int(qid))
    elif item.get("positive"):
        qid = item["positive"].get("qual_id")
        if qid is not None:
            ids.append(int(qid))
    return tuple(sorted(set(ids)))


def sample_key(item: dict) -> tuple:
    """동일 샘플 판별용 키: (raw_query 정규화, positive_qual_ids)."""
    raw = (item.get("raw_query") or "").strip()
    raw = " ".join(raw.split())
    ids = get_positive_qual_ids(item)
    return (raw, ids)


def load_json(path: Path):
    """JSON 파일 로드. 배열이 아니면 배열로 래핑."""
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        return [data]
    return data


def dedup_items(items: list) -> list:
    """(raw_query, positive 집합) 동일 시 1건만 유지. negative 많은 row 우선."""
    groups = defaultdict(list)
    for i, item in enumerate(items):
        key = sample_key(item)
        groups[key].append((i, item))

    kept = []
    for key, group in groups.items():
        group_sorted = sorted(
            group,
            key=lambda x: (-len(x[1].get("negatives") or []), x[0]),
        )
        kept.append(group_sorted[0][1])

    first_index = {key: min(i for i, _ in g) for key, g in groups.items()}
    kept.sort(key=lambda item: first_index[sample_key(item)])
    return kept


def run(
    base_path: str,
    new_path: str,
    out_path: str,
    dedup: bool = False,
) -> dict:
    base_p = Path(base_path)
    new_p = Path(new_path)
    out_p = Path(out_path)

    if not base_p.exists():
        raise FileNotFoundError(f"Base file not found: {base_path}")
    if not new_p.exists():
        raise FileNotFoundError(f"New file not found: {new_path}")

    base_items = load_json(base_p)
    new_items = load_json(new_p)
    combined = base_items + new_items

    if dedup:
        before = len(combined)
        combined = dedup_items(combined)
        removed = before - len(combined)
    else:
        removed = 0

    for idx, item in enumerate(combined):
        item["query_id"] = f"p{idx + 1:03d}"

    out_p.parent.mkdir(parents=True, exist_ok=True)
    with open(out_p, "w", encoding="utf-8") as f:
        json.dump(combined, f, ensure_ascii=False, indent=2)

    return {
        "base_count": len(base_items),
        "new_count": len(new_items),
        "total_after_merge": len(base_items) + len(new_items),
        "total_after_dedup": len(combined),
        "removed_by_dedup": removed,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Merge base + new contrastive profile JSON and renumber query_id."
    )
    parser.add_argument(
        "--base",
        default="data/contrastive_profile_train_example.json",
        help="Path to existing contrastive profile JSON array",
    )
    parser.add_argument(
        "--new",
        required=True,
        help="Path to newly generated JSON array to append",
    )
    parser.add_argument(
        "--out",
        default="",
        help="Output path (default: same as --base, overwrite)",
    )
    parser.add_argument(
        "--dedup",
        action="store_true",
        help="Remove duplicate rows (same raw_query + same positive set); keep row with more negatives",
    )
    args = parser.parse_args()

    out_path = args.out.strip() or args.base

    try:
        res = run(args.base, args.new, out_path, dedup=args.dedup)
    except FileNotFoundError as e:
        print(e, file=sys.stderr)
        return 1
    except Exception as e:
        print(e, file=sys.stderr)
        return 1

    print(f"Base: {res['base_count']} rows, New: {res['new_count']} rows")
    print(f"After merge: {res['total_after_merge']} rows")
    if args.dedup:
        print(f"After dedup: {res['total_after_dedup']} rows (removed: {res['removed_by_dedup']})")
    print(f"Written to: {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
