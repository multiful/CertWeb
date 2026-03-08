"""
contrastive_profile_train_example.json 에서
맥락상 여러 정답이 plausible한 row는 single positive → positives 배열로 확장.

- 데이터분석/데이터 직무/빅데이터: ADsP, SQLD, 빅데이터분석기사 (필요 시 정보처리기사)
- 개발/IT 취업: 정보처리기사, SQLD, ADsP
- DB/데이터베이스: SQLD, 정보처리기사, ADsP
"""
import json
import re
import sys
from pathlib import Path


def build_cert_lookup(items: list) -> dict:
    """qual_name -> {qual_id, qual_name, text} (첫 등장 기준)."""
    lookup = {}
    for item in items:
        for src in ("positive", "positives", "negatives"):
            if src == "positive":
                objs = [item[src]] if item.get(src) else []
            elif src == "positives":
                objs = item.get(src) or []
            else:
                objs = item.get("negatives") or []
            for o in objs:
                if not isinstance(o, dict):
                    continue
                name = (o.get("qual_name") or "").strip()
                if not name or name in lookup:
                    continue
                lookup[name] = {
                    "qual_id": o.get("qual_id"),
                    "qual_name": name,
                    "text": o.get("text") or "",
                }
    return lookup


def context_string(item: dict) -> str:
    raw = (item.get("raw_query") or "").lower()
    rew = (item.get("rewritten_query") or "").replace("\n", " ").lower()
    return raw + " " + rew


def is_data_context(ctx: str) -> bool:
    return bool(
        re.search(
            r"데이터\s*(분석|직무|활용|기반|관련)?|빅데이터|데이터분석|데이터베이스|db\s|sql",
            ctx,
        )
    )


def is_dev_it_context(ctx: str) -> bool:
    return bool(
        re.search(
            r"개발|it\s*쪽|it\s*취업|전산|프로그래밍|소프트웨어|시스템\s*구축|데이터베이스|정보처리",
            ctx,
        )
    )


# IT/데이터 계열만 multi-positive 확장 대상 (사무/회계/비서 등은 단일 positive 유지)
IT_DATA_POSITIVE_NAMES = {"정보처리기사", "SQLD", "ADsP", "빅데이터분석기사"}

# 맥락별 추가할 plausible positive 후보 (자격증명)
DATA_EXTRA = ["ADsP", "SQLD", "빅데이터분석기사"]
DEV_IT_EXTRA = ["정보처리기사", "SQLD", "ADsP"]
DB_EXTRA = ["SQLD", "정보처리기사", "ADsP"]


def get_extra_positives_for_context(ctx: str, current_qual_name: str) -> list[str]:
    """현재 positive를 제외한, 맥락상 plausible한 추가 positive 후보명 목록.
    이미 positive가 IT/데이터 계열(정보처리기사, SQLD, ADsP, 빅데이터분석기사)일 때만 확장.
    """
    current = (current_qual_name or "").strip()
    if current not in IT_DATA_POSITIVE_NAMES:
        return []
    added = set()
    if is_data_context(ctx):
        for c in DATA_EXTRA:
            if c != current:
                added.add(c)
    if is_dev_it_context(ctx):
        for c in DEV_IT_EXTRA:
            if c != current:
                added.add(c)
    if re.search(r"데이터베이스|db\s|sql", ctx):
        for c in DB_EXTRA:
            if c != current:
                added.add(c)
    return list(added)


def run(input_path: str, output_path: str = "", dry_run: bool = False) -> dict:
    path = Path(input_path)
    if not path.exists():
        raise FileNotFoundError(input_path)
    out_path = Path(output_path) if output_path else path

    with open(path, "r", encoding="utf-8") as f:
        items = json.load(f)

    cert_lookup = build_cert_lookup(items)
    expanded = 0
    for item in items:
        if "positives" in item and item["positives"]:
            continue
        pos = item.get("positive")
        if not pos:
            continue
        current_name = (pos.get("qual_name") or "").strip()
        if not current_name:
            continue
        ctx = context_string(item)
        extra_names = get_extra_positives_for_context(ctx, current_name)
        if not extra_names:
            continue
        # 현재 + 추가 후보 중 lookup에 있는 것만
        all_names = [current_name]
        for name in extra_names:
            if name in cert_lookup and name not in all_names:
                all_names.append(name)
        if len(all_names) <= 1:
            continue
        # positives 배열로 변환 (qual_id 순으로 고정해 두기 위해 순서 유지)
        order_key = {"정보처리기사": 0, "SQLD": 1, "ADsP": 2, "빅데이터분석기사": 3}
        all_names.sort(key=lambda x: (order_key.get(x, 99), x))
        positives = [cert_lookup[n] for n in all_names if n in cert_lookup]
        if len(positives) <= 1:
            continue
        item["positives"] = positives
        del item["positive"]
        expanded += 1
        if dry_run:
            print(f"  {item.get('query_id')} | {current_name} -> {[p['qual_name'] for p in positives]}")

    if not dry_run and expanded > 0:
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(items, f, ensure_ascii=False, indent=2)

    return {"expanded_rows": expanded, "total_rows": len(items)}


def main():
    import argparse
    ap = argparse.ArgumentParser(description="Single positive → positives 확장")
    ap.add_argument("--data", default="data/contrastive_profile_train_example.json")
    ap.add_argument("--out", default="")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    try:
        res = run(args.data, args.out, dry_run=args.dry_run)
    except Exception as e:
        print(e, file=sys.stderr)
        return 1
    print(f"Expanded {res['expanded_rows']} rows to multi-positive (total {res['total_rows']})")
    if args.dry_run and res["expanded_rows"]:
        print("(dry-run: no file written)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
