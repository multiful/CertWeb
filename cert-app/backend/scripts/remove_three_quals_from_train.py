# -*- coding: utf-8 -*-
"""인사관리사, 노동관리사, 부동산거래관리사 참조를 contrastive train JSON 전체에서 제거."""
import json
import sys
from pathlib import Path

REMOVE_NAMES = {"인사관리사", "노동관리사", "부동산거래관리사"}

def main():
    path = Path("data/contrastive_profile_train_merged_supabase_ids.json")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        sys.exit("Not an array")
    out = []
    for row in data:
        if not isinstance(row, dict):
            continue
        row = dict(row)
        # Remove single positive if it's one of the 3
        if row.get("positive") and isinstance(row["positive"], dict):
            if (row["positive"].get("qual_name") or "").strip() in REMOVE_NAMES:
                del row["positive"]
        # Filter positives array
        if "positives" in row and isinstance(row["positives"], list):
            row["positives"] = [p for p in row["positives"] if isinstance(p, dict) and (p.get("qual_name") or "").strip() not in REMOVE_NAMES]
        # Filter negatives
        if "negatives" in row and isinstance(row["negatives"], list):
            row["negatives"] = [n for n in row["negatives"] if isinstance(n, dict) and (n.get("qual_name") or "").strip() not in REMOVE_NAMES]
        # Drop row if no positives left
        has_single = row.get("positive") and isinstance(row["positive"], dict) and (row["positive"].get("qual_name") or "").strip()
        has_multi = row.get("positives") and len(row["positives"]) > 0
        if not (has_single or has_multi):
            continue
        out.append(row)
    path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Removed 3 quals from train JSON. Rows: {len(data)} -> {len(out)}")

if __name__ == "__main__":
    main()
