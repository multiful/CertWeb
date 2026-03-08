"""
contrastive_profile_train_example.json 에서
'합리적 대안(plausible alternative)'이 잘못 negative로 들어간 항목을 제거해 네거티브를 느슨하게 보완.

규칙:
- 데이터분석/데이터 직무/빅데이터 관련 질의 → ADsP, SQLD, 빅데이터분석기사는 plausible → negative에서 제거
- 개발/IT 취업 관련 질의 → 정보처리기사, SQLD, ADsP는 plausible → negative에서 제거
- 사무직/OA/공기업 컴활 질의(positive=컴활) → 정보처리기사/SQLD는 목적 다름 → 유지 가능
- 서버/네트워크/인프라 직무 질의 → ADsP/SQLD/데이터 계열은 직무 다름 → 유지
"""
import json
import re
import sys
from pathlib import Path


def get_positives_names_and_text(item: dict) -> list[tuple[str, str]]:
    out = []
    if "positives" in item and item["positives"]:
        for p in item["positives"]:
            out.append((p.get("qual_name") or "", (p.get("text") or "")[:200]))
    elif item.get("positive"):
        p = item["positive"]
        out.append((p.get("qual_name") or "", (p.get("text") or "")[:200]))
    return out


def context_string(item: dict) -> str:
    raw = (item.get("raw_query") or "").lower()
    rew = (item.get("rewritten_query") or "").replace("\n", " ").lower()
    pos_parts = []
    for name, text in get_positives_names_and_text(item):
        pos_parts.append(name.lower())
        pos_parts.append(text.lower())
    return raw + " " + rew + " " + " ".join(pos_parts)


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


def is_office_context(ctx: str) -> bool:
    return bool(
        re.search(r"사무직|사무\s*쪽|oa|컴퓨터활용|공기업|문서\s*작성", ctx)
    )


def is_infra_context(ctx: str) -> bool:
    # 서버/네트워크/인프라 직무. "운영체제"(OS)·"시스템 구축"은 제외(시스템\s*운영은 직무 의미로만)
    return bool(
        re.search(
            r"서버\s*(운영|관리)?|네트워크\s*(운영|관리)?|인프라\s*(관리|운영)?|시스템\s+운영\b|리눅스\s*마스터",
            ctx,
        )
    )


# 진짜 부적합(합리적 대안 아님): 학년/목적에 비해 너무 어렵거나, 이미 취득보다 하위 등
TRULY_INAPPROPRIATE_TYPES = {
    "too_advanced_for_grade",
    "too_advanced_for_goal",
    "lower_than_acquired",
    "already_acquired_level",
    "far_too_basic",
    "far_too_easy",
    "too_easy_given_acquired",  # 이미 취득 후 다음 단계 찾을 때 하위 자격은 대안 아님
}

# 자격증별: 어떤 맥락에서 plausible인지
DATA_PLAUSIBLE = {"ADsP", "SQLD", "빅데이터분석기사"}
DEV_IT_PLAUSIBLE = {"정보처리기사", "SQLD", "ADsP"}


def should_remove_negative(
    item: dict,
    neg_qual_name: str,
    neg_type: str,
    ctx: str,
) -> bool:
    """합리적 대안이면 제거(True). negative_type 무관하게 '맥락상 plausible'이면 제거."""
    name = (neg_qual_name or "").strip()
    if not name:
        return False
    if name not in (DATA_PLAUSIBLE | DEV_IT_PLAUSIBLE):
        return False

    # 진짜 부적합이면 negative 유지 (제거하지 않음)
    if neg_type in TRULY_INAPPROPRIATE_TYPES:
        return False

    # 서버/네트워크/인프라 맥락: 데이터/개발 계열은 직무가 다르므로 유지
    if is_infra_context(ctx):
        return False

    # 사무직/OA/공기업 컴활 질의(positive=컴활): 목적이 다르므로 유지
    if is_office_context(ctx):
        pos_names = []
        if "positives" in item and item["positives"]:
            pos_names = [p.get("qual_name") or "" for p in item["positives"]]
        elif item.get("positive"):
            pos_names = [item["positive"].get("qual_name") or ""]
        pos_str = " ".join(pos_names)
        if "컴퓨터활용능력" in pos_str or "컴활" in pos_str:
            return False

    # 데이터 맥락: ADsP, SQLD, 빅데이터분석기사는 합리적 대안 → 제거
    if is_data_context(ctx) and name in DATA_PLAUSIBLE:
        return True
    if is_data_context(ctx) and name == "정보처리기사" and is_dev_it_context(ctx):
        return True

    # 개발/IT/DB 맥락: 정보처리기사, SQLD, ADsP는 합리적 대안 → 제거
    if is_dev_it_context(ctx) and name in DEV_IT_PLAUSIBLE:
        return True
    # 개발 직무 질의에서 빅데이터분석기사도 데이터 확장 대안으로 plausible
    if is_dev_it_context(ctx) and name == "빅데이터분석기사":
        return True

    return False


def run(input_path: str, output_path: str = "", dry_run: bool = False) -> dict:
    path = Path(input_path)
    if not path.exists():
        raise FileNotFoundError(input_path)
    out_path = Path(output_path) if output_path else path

    with open(path, "r", encoding="utf-8") as f:
        items = json.load(f)

    removed_count = 0
    rows_changed = 0
    for item in items:
        ctx = context_string(item)
        negatives = item.get("negatives") or []
        if not negatives:
            continue
        kept = []
        for n in negatives:
            neg_name = n.get("qual_name") or ""
            neg_type = n.get("negative_type") or ""
            if should_remove_negative(item, neg_name, neg_type, ctx):
                removed_count += 1
                continue
            kept.append(n)
        if len(kept) != len(negatives):
            rows_changed += 1
            item["negatives"] = kept

    if not dry_run and (removed_count > 0 or rows_changed > 0):
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(items, f, ensure_ascii=False, indent=2)

    return {
        "removed_negatives": removed_count,
        "rows_changed": rows_changed,
        "total_rows": len(items),
    }


def main():
    import argparse
    ap = argparse.ArgumentParser(description="Contrastive JSON에서 합리적 대안 negative 제거")
    ap.add_argument("--data", default="data/contrastive_profile_train_example.json")
    ap.add_argument("--out", default="", help="출력 경로 (기본: 입력 덮어쓰기)")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    try:
        res = run(args.data, args.out, dry_run=args.dry_run)
    except Exception as e:
        print(e, file=sys.stderr)
        return 1
    print(f"Removed {res['removed_negatives']} negatives from {res['rows_changed']} rows (total {res['total_rows']})")
    if args.dry_run and res["removed_negatives"]:
        print("(dry-run: no file written)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
