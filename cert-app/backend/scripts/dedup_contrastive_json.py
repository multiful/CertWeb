"""
contrastive_profile_train_example.json 중복 제거.

- 완전 중복: raw_query + positive 집합(+ profile) 동일 → 1건만 유지
- 같은 query + 같은 positive 집합, negative만 다름 → 1건만 유지 (negative 많은 것 우선)
- query_id 재부여: p001, p002, ... 연속
"""
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
    # 공백 정규화
    raw = " ".join(raw.split())
    ids = get_positive_qual_ids(item)
    return (raw, ids)


def run(input_path: str, output_path: str = "", dry_run: bool = False) -> dict:
    path = Path(input_path)
    if not path.exists():
        raise FileNotFoundError(input_path)
    out_path = Path(output_path) if output_path else path

    with open(path, "r", encoding="utf-8") as f:
        items = json.load(f)

    # key -> list of (index, item)
    groups = defaultdict(list)
    for i, item in enumerate(items):
        key = sample_key(item)
        groups[key].append((i, item))

    # 그룹별로 1건만 유지 (negative 수가 많은 것 우선, 동일하면 첫 등장)
    kept = []
    for key, group in groups.items():
        # negative 개수 내림차순, 동일하면 원래 순서
        group_sorted = sorted(
            group,
            key=lambda x: (-len(x[1].get("negatives") or []), x[0]),
        )
        kept.append(group_sorted[0][1])

    # 원래 순서 유지: key 순이 아니라 첫 등장한 item의 인덱스 순
    first_index = {}
    for key, group in groups.items():
        first_index[key] = min(i for i, _ in group)
    kept.sort(key=lambda item: first_index[sample_key(item)])

    # query_id 재부여 p001, p002, ...
    for idx, item in enumerate(kept):
        item["query_id"] = f"p{idx + 1:03d}"

    removed = len(items) - len(kept)
    if not dry_run:
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(kept, f, ensure_ascii=False, indent=2)

    return {
        "total_before": len(items),
        "total_after": len(kept),
        "removed": removed,
        "groups_with_dupes": sum(1 for g in groups.values() if len(g) > 1),
    }


def main():
    import argparse
    ap = argparse.ArgumentParser(description="Contrastive JSON 중복 row 제거")
    ap.add_argument("--data", default="data/contrastive_profile_train_example.json")
    ap.add_argument("--out", default="")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    try:
        res = run(args.data, args.out, dry_run=args.dry_run)
    except Exception as e:
        print(e, file=sys.stderr)
        return 1
    print(f"Before: {res['total_before']} rows, After: {res['total_after']} rows, Removed: {res['removed']}")
    print(f"Groups that had duplicates: {res['groups_with_dupes']}")
    if args.dry_run and res["removed"]:
        print("(dry-run: no file written)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
