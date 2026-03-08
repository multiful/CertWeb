"""
contrastive JSON에서 '합리적 대안'이 negative로 남아 있는지 전수 검사.
각 row별로 negative 목록과 맥락을 출력해 검토용으로 사용.
"""
import argparse
import json
import re
import sys
from pathlib import Path

PLAUSIBLE_CERTS = {"ADsP", "SQLD", "정보처리기사", "빅데이터분석기사"}


def get_positive_names(item: dict) -> list[str]:
    names = []
    if "positives" in item and item["positives"]:
        for p in item["positives"]:
            n = (p.get("qual_name") or "").strip()
            if n:
                names.append(n)
    elif item.get("positive"):
        n = (item["positive"].get("qual_name") or "").strip()
        if n:
            names.append(n)
    return names


def context_string(item: dict) -> str:
    raw = (item.get("raw_query") or "").lower()
    rew = (item.get("rewritten_query") or "").replace("\n", " ").lower()
    pos = " ".join(get_positive_names(item)).lower()
    return raw + " " + rew + " " + pos


def is_data_related(ctx: str) -> bool:
    return bool(
        re.search(
            r"데이터\s*(분석|직무|활용|기반|관련)?|빅데이터|데이터분석|데이터베이스|db\s|sql",
            ctx,
        )
    )


def is_dev_it_related(ctx: str) -> bool:
    return bool(
        re.search(
            r"개발|it\s*쪽|it\s*취업|전산|프로그래밍|소프트웨어|시스템\s*구축|데이터베이스|정보처리",
            ctx,
        )
    )


def is_infra_related(ctx: str) -> bool:
    return bool(
        re.search(r"서버|네트워크|인프라|시스템\s*운영|리눅스", ctx)
    )


def is_office_primary(ctx: str, pos_names: list[str]) -> bool:
    if not re.search(r"사무직|사무\s*쪽|oa|공기업|문서\s*작성", ctx):
        return False
    return "컴퓨터활용능력" in " ".join(pos_names) or "컴활" in ctx


def is_truly_inappropriate(neg_type: str) -> bool:
    """진짜 부적합(이미 취득보다 하위, 학년에 비해 너무 어려움 등)이면 True."""
    return neg_type in (
        "too_advanced_for_grade",
        "too_advanced_for_goal",
        "lower_than_acquired",
        "already_acquired_level",
        "far_too_basic",
        "far_too_easy",
        "too_easy_given_acquired",
    )


def is_plausible_alternative(
    neg_name: str,
    neg_type: str,
    ctx: str,
    pos_names: list[str],
) -> bool:
    """이 negative가 이 질의 맥락에서 '합리적 대안'이면 True (제거 대상)."""
    if neg_name not in PLAUSIBLE_CERTS:
        return False
    if is_truly_inappropriate(neg_type):
        return False
    if is_infra_related(ctx):
        return False
    if is_office_primary(ctx, pos_names):
        return False

    # 데이터/빅데이터 맥락 → ADsP, SQLD, 빅데이터분석기사, 정보처리기사(데이터+개발 겸) 모두 대안 가능
    if is_data_related(ctx):
        if neg_name in ("ADsP", "SQLD", "빅데이터분석기사"):
            return True
        if neg_name == "정보처리기사" and is_dev_it_related(ctx):
            return True

    # 개발/IT/DB 맥락 → 정보처리기사, SQLD, ADsP 대안 가능
    if is_dev_it_related(ctx):
        if neg_name in ("정보처리기사", "SQLD", "ADsP"):
            return True
        if neg_name == "빅데이터분석기사" and is_data_related(ctx):
            return True

    return False


def run(input_path: str) -> list[dict]:
    path = Path(input_path)
    with open(path, "r", encoding="utf-8") as f:
        items = json.load(f)

    issues = []
    for item in items:
        qid = item.get("query_id") or ""
        raw = (item.get("raw_query") or "").strip()
        ctx = context_string(item)
        pos_names = get_positive_names(item)
        for n in item.get("negatives") or []:
            neg_name = (n.get("qual_name") or "").strip()
            if neg_name not in PLAUSIBLE_CERTS:
                continue
            neg_type = n.get("negative_type") or ""
            if is_plausible_alternative(neg_name, neg_type, ctx, pos_names):
                issues.append({
                    "query_id": qid,
                    "raw_query": raw,
                    "positive": pos_names,
                    "negative_cert": neg_name,
                    "negative_type": neg_type,
                })
    return issues


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="data/contrastive_profile_train_example.json")
    args = ap.parse_args()
    issues = run(args.data)
    for i in issues:
        print(f"[{i['query_id']}] {i['raw_query'][:50]}... | positive={i['positive']} | negative={i['negative_cert']} ({i['negative_type']})")
    print(f"\nTotal: {len(issues)} plausible-alternative negatives still in file (should be 0).")
    return 1 if issues else 0


if __name__ == "__main__":
    sys.exit(main())
