# -*- coding: utf-8 -*-
"""
Contrastive 학습용 JSON 정제: qual_id 보정, negative_type 표준화, negative 5개 보강, 중복 제거, audit 저장.

실행 예:
  uv run python scripts/clean_contrastive_dataset.py --train data/contrastive_profile_train_merged_supabase_ids.json --corpus data/all_cert_corpus.json
  uv run python scripts/clean_contrastive_dataset.py --train data/contrastive_profile_train_merged_supabase_ids.json --corpus data/all_cert_corpus.json --out data/contrastive_profile_train_merged_supabase_ids.json --audit data/clean_contrastive_audit.json --dry-run
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# 표준 negative_type 5종
STANDARD_NEGATIVE_TYPES = [
    "same_domain_different_role",
    "same_level_but_wrong_track",
    "lower_than_acquired",
    "bookmark_confusion",
    "retrieved_topk_confusion",
]

# 기존 negative_type -> 표준 타입 매핑 (우선순위: 위에서부터 매칭)
NEGATIVE_TYPE_NORMALIZE: List[Tuple[List[str], str]] = [
    (["too_basic", "too_easy", "lower_level_office", "too_easy_given_acquired", "too_basic_office", "too_basic_given_profile", "far_too_basic", "office_basic", "too_advanced_for_freshman", "too_advanced_for_grade"], "lower_than_acquired"),
    (["bookmark_confusable", "current_interest_but_wrong_goal"], "bookmark_confusion"),
    (["mined_topk_confusion", "retrieval_frequent_false_positive", "retrieval_frequent_false_positive"], "retrieved_topk_confusion"),
    (["same_it_but_wrong_job", "same_data_domain_wrong_job", "wrong_domain", "infra_role", "office_domain", "it_but_wrong_focus", "different_office_domain", "business_but_not_it", "industrial_but_not_it", "good_but_not_primary_goal", "it_specialized", "data_not_infra", "office_only", "unrelated_domain", "different_domain", "same_qual_type", "same_target_different_job", "adjacent_data_role"], "same_domain_different_role"),
    (["same_level_but_wrong_track"], "same_level_but_wrong_track"),
]
# lower_than_acquired / bookmark_confusion / retrieved_topk_confusion 은 이미 표준명이면 유지
for _std in STANDARD_NEGATIVE_TYPES:
    NEGATIVE_TYPE_NORMALIZE.append(([_std], _std))


def load_json(path: Path) -> Any:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def build_corpus_lookup(corpus: List[Dict]) -> Tuple[Dict[str, int], List[Dict[str, Any]]]:
    """qual_name -> qual_id (정확 일치), 및 포함 관계용 (name, id, text) 리스트."""
    exact: Dict[str, int] = {}
    name_id_list: List[Tuple[str, int, str]] = []
    for item in corpus:
        if not isinstance(item, dict):
            continue
        name = (item.get("qual_name") or "").strip()
        qid = item.get("qual_id")
        text = item.get("text") or ""
        if not name or qid is None:
            continue
        try:
            qid = int(qid)
        except (TypeError, ValueError):
            continue
        if name not in exact:
            exact[name] = qid
        name_id_list.append((name, qid, text))
    return exact, name_id_list


def resolve_qual_id(name: str, exact: Dict[str, int], name_id_list: List[Tuple[str, int, str]]) -> Optional[int]:
    """qual_name으로 corpus에서 qual_id 조회. 정확 일치 -> 포함 관계."""
    n = (name or "").strip()
    if not n:
        return None
    if n in exact:
        return exact[n]
    # train 이름이 코퍼스 이름에 포함 (예: 전산회계 1급 -> 전산세무회계 전산회계 1급)
    contained = [(qid, cname) for cname, qid, _ in name_id_list if n in cname]
    if contained:
        return min(contained, key=lambda x: len(x[1]))[0]
    # 코퍼스 이름이 train 이름에 포함
    reverse = [(qid, cname) for cname, qid, _ in name_id_list if cname in n]
    if reverse:
        return max(reverse, key=lambda x: len(x[1]))[0]
    return None


def normalize_negative_type(nt: str) -> str:
    if not nt:
        return "retrieved_topk_confusion"
    nt = (nt or "").strip()
    for variants, standard in NEGATIVE_TYPE_NORMALIZE:
        if nt in variants or nt == standard:
            return standard
    return "retrieved_topk_confusion"


def get_positive_qual_names(row: Dict) -> Set[str]:
    out: Set[str] = set()
    for p in row.get("positives") or []:
        if isinstance(p, dict) and p.get("qual_name"):
            out.add((p.get("qual_name") or "").strip())
    single = row.get("positive")
    if isinstance(single, dict) and single.get("qual_name"):
        out.add((single.get("qual_name") or "").strip())
    return out


def sample_key(row: Dict) -> Tuple:
    raw = " ".join((row.get("raw_query") or "").split())
    profile = row.get("profile") or {}
    major = " ".join((profile.get("major") or "").split())
    grade = profile.get("grade_level")
    fav = tuple(sorted((profile.get("favorite_cert_names") or [])))
    acq = tuple(sorted((profile.get("acquired_cert_names") or [])))
    pos_set = tuple(sorted(get_positive_qual_names(row)))
    return (raw, major, grade, fav, acq, pos_set)


def fix_qual_ids_in_row(row: Dict, exact: Dict[str, int], name_id_list: List[Tuple[str, int, str]], audit: Dict, row_idx: int) -> None:
    def fix_item(item: Dict, kind: str) -> None:
        if not isinstance(item, dict):
            return
        name = (item.get("qual_name") or "").strip()
        if not name:
            return
        resolved = resolve_qual_id(name, exact, name_id_list)
        if resolved is not None:
            old = item.get("qual_id")
            if old != resolved:
                item["qual_id"] = resolved
                audit.setdefault("qual_id_fixed", []).append({"row_index": row_idx, "qual_name": name, "kind": kind, "old": old, "new": resolved})
        else:
            if "qual_id" not in item or item["qual_id"] is None:
                audit.setdefault("qual_id_not_found", []).append({"row_index": row_idx, "qual_name": name, "kind": kind})

    single = row.get("positive")
    if single and isinstance(single, dict):
        fix_item(single, "positive")
    for p in row.get("positives") or []:
        if isinstance(p, dict):
            fix_item(p, "positives")
    for n in row.get("negatives") or []:
        if isinstance(n, dict):
            fix_item(n, "negatives")


def normalize_negatives_in_row(row: Dict, audit: Dict, row_idx: int) -> None:
    negs = row.get("negatives") or []
    if not isinstance(negs, list):
        return
    for n in negs:
        if not isinstance(n, dict):
            continue
        old_nt = n.get("negative_type") or ""
        new_nt = normalize_negative_type(old_nt)
        if old_nt != new_nt:
            n["negative_type"] = new_nt
            audit.setdefault("negative_type_normalized", []).append({"row_index": row_idx, "qual_name": n.get("qual_name"), "old": old_nt, "new": new_nt})


def remove_plausible_positive_from_negatives(row: Dict, exact: Dict[str, int], name_id_list: List[Tuple[str, int, str]], corpus_list: List[Dict], audit: Dict, row_idx: int) -> None:
    pos_names = get_positive_qual_names(row)
    negs = row.get("negatives") or []
    to_remove = []
    for i, n in enumerate(negs):
        if not isinstance(n, dict):
            continue
        name = (n.get("qual_name") or "").strip()
        if name in pos_names:
            to_remove.append(i)
            audit.setdefault("plausible_positive_removed_from_negatives", []).append({"row_index": row_idx, "query_id": row.get("query_id"), "qual_name": name})
    for i in reversed(to_remove):
        negs.pop(i)


def fill_negatives_to_five(row: Dict, exact: Dict[str, int], name_id_list: List[Tuple[str, int, str]], corpus_list: List[Dict], audit: Dict, row_idx: int) -> None:
    """row의 negatives를 표준 5타입 각 1개씩으로 정확히 5개가 되도록 보강/축소."""
    pos_names = get_positive_qual_names(row)
    negs = list(row.get("negatives") or [])
    by_type: Dict[str, List[Dict]] = defaultdict(list)
    for n in negs:
        if not isinstance(n, dict):
            continue
        nt = normalize_negative_type(n.get("negative_type") or "")
        by_type[nt].append(n)

    used_neg_names: Set[str] = set()
    for n in negs:
        if isinstance(n, dict) and n.get("qual_name"):
            used_neg_names.add((n.get("qual_name") or "").strip())

    def make_negative_entry(qual_name: str, negative_type: str) -> Dict:
        qid = resolve_qual_id(qual_name, exact, name_id_list)
        text = ""
        for c in corpus_list:
            if isinstance(c, dict) and (c.get("qual_name") or "").strip() == qual_name:
                text = c.get("text") or ""
                break
        if not text and qual_name:
            text = f"자격증명: {qual_name}\n자격종류: -\n관련직무: -\n설명: -"
        entry = {"qual_name": qual_name, "negative_type": negative_type, "text": text}
        if qid is not None:
            entry["qual_id"] = qid
        return entry

    added = []
    final_negatives: List[Dict] = []
    for std_type in STANDARD_NEGATIVE_TYPES:
        chosen = None
        if by_type[std_type]:
            chosen = by_type[std_type][0]
        else:
            candidate = None
            for c in corpus_list:
                if not isinstance(c, dict):
                    continue
                name = (c.get("qual_name") or "").strip()
                if not name or name in pos_names or name in used_neg_names:
                    continue
                candidate = name
                used_neg_names.add(name)
                break
            if not candidate:
                for c in corpus_list:
                    if not isinstance(c, dict):
                        continue
                    name = (c.get("qual_name") or "").strip()
                    if not name or name in pos_names or name in used_neg_names:
                        continue
                    candidate = name
                    used_neg_names.add(name)
                    break
            if candidate:
                chosen = make_negative_entry(candidate, std_type)
                added.append({"negative_type": std_type, "qual_name": candidate})
        if chosen:
            final_negatives.append(chosen)
    if added:
        audit.setdefault("negatives_filled", []).append({"row_index": row_idx, "query_id": row.get("query_id"), "added": added})
    row["negatives"] = final_negatives


def deduplicate_rows(rows: List[Dict], audit: Dict) -> List[Dict]:
    groups: Dict[Tuple, List[Tuple[int, Dict]]] = defaultdict(list)
    for i, r in enumerate(rows):
        k = sample_key(r)
        groups[k].append((i, r))
    kept = []
    for k, group in groups.items():
        # negative 개수 많은 순, 동일하면 첫 번째
        best = max(group, key=lambda x: (len((x[1].get("negatives") or [])), -x[0]))
        idx, r = best
        kept.append(r)
        if len(group) > 1:
            removed_indices = [i for i, _ in group if i != idx]
            audit.setdefault("duplicates_removed", []).append({"key": list(k), "kept_index": idx, "removed_indices": removed_indices, "query_id": r.get("query_id")})
    # 원래 순서 유지 (첫 등장 인덱스 기준)
    first_idx = {sample_key(r): min(i for i, _ in groups[sample_key(r)]) for r in kept}
    kept.sort(key=lambda r: first_idx[sample_key(r)])
    return kept


def renumber_query_ids(rows: List[Dict]) -> None:
    for i, r in enumerate(rows):
        r["query_id"] = f"p{i + 1:03d}"


def validate_schema(rows: List[Dict]) -> List[str]:
    errors = []
    for i, r in enumerate(rows):
        if not isinstance(r, dict):
            errors.append(f"row {i}: not a dict")
            continue
        if not r.get("raw_query") and not r.get("rewritten_query"):
            errors.append(f"row {i}: missing raw_query/rewritten_query")
        if "positive" not in r and "positives" not in r:
            errors.append(f"row {i}: missing both positive and positives")
        if "positive" in r and "positives" in r and r["positives"]:
            errors.append(f"row {i}: has both positive and non-empty positives")
        negs = r.get("negatives") or []
        if len(negs) < 5:
            errors.append(f"row {i}: negatives count {len(negs)} < 5")
        for n in negs:
            if not isinstance(n, dict) or not n.get("qual_name") or not n.get("negative_type"):
                errors.append(f"row {i}: invalid negative entry")
                break
    return errors


def run(
    train_path: Path,
    corpus_path: Path,
    out_path: Optional[Path] = None,
    audit_path: Optional[Path] = None,
    dry_run: bool = False,
) -> Dict[str, Any]:
    if not train_path.exists():
        raise FileNotFoundError(f"Train file not found: {train_path}")
    if not corpus_path.exists():
        raise FileNotFoundError(f"Corpus file not found: {corpus_path}")

    train_data = load_json(train_path)
    if not isinstance(train_data, list):
        raise ValueError("Train JSON root must be an array")
    corpus_data = load_json(corpus_path)
    if not isinstance(corpus_data, list):
        raise ValueError("Corpus JSON root must be an array")

    exact, name_id_list = build_corpus_lookup(corpus_data)
    logger.info("Corpus lookup: %s exact qual_name -> qual_id", len(exact))

    audit: Dict[str, Any] = {"summary": {}, "qual_id_fixed": [], "qual_id_not_found": [], "negative_type_normalized": [], "plausible_positive_removed_from_negatives": [], "negatives_filled": [], "duplicates_removed": [], "schema_errors": []}
    rows = list(train_data)
    n_before = len(rows)

    for i, row in enumerate(rows):
        if not isinstance(row, dict):
            continue
        fix_qual_ids_in_row(row, exact, name_id_list, audit, i)
        normalize_negatives_in_row(row, audit, i)
        remove_plausible_positive_from_negatives(row, exact, name_id_list, corpus_data, audit, i)
        fill_negatives_to_five(row, exact, name_id_list, corpus_data, audit, i)

    rows = deduplicate_rows(rows, audit)
    renumber_query_ids(rows)
    schema_errors = validate_schema(rows)
    audit["schema_errors"] = schema_errors
    if schema_errors:
        for e in schema_errors[:10]:
            logger.warning("Schema: %s", e)
        if len(schema_errors) > 10:
            logger.warning("... and %s more schema errors", len(schema_errors) - 10)

    audit["summary"] = {
        "rows_before": n_before,
        "rows_after": len(rows),
        "qual_id_fixed_count": len(audit.get("qual_id_fixed", [])),
        "qual_id_not_found_count": len(audit.get("qual_id_not_found", [])),
        "negative_type_normalized_count": len(audit.get("negative_type_normalized", [])),
        "plausible_removed_count": len(audit.get("plausible_positive_removed_from_negatives", [])),
        "negatives_filled_count": len(audit.get("negatives_filled", [])),
        "duplicates_removed_count": len(audit.get("duplicates_removed", [])),
        "schema_error_count": len(schema_errors),
    }

    out = out_path or train_path
    if not dry_run:
        save_json(out, rows)
        logger.info("Saved cleaned JSON: %s (%s rows)", out, len(rows))
    if audit_path and not dry_run:
        save_json(audit_path, audit)
        logger.info("Saved audit: %s", audit_path)
    logger.info("Summary: %s", audit["summary"])
    return {"rows": rows, "audit": audit}


def main() -> int:
    parser = argparse.ArgumentParser(description="Clean contrastive train JSON: qual_id, negative_type, 5 negatives, dedup")
    parser.add_argument("--train", "-t", type=Path, default=Path("data/contrastive_profile_train_merged_supabase_ids.json"), help="Input train JSON")
    parser.add_argument("--corpus", "-c", type=Path, default=Path("data/all_cert_corpus.json"), help="Corpus JSON (qual_name, qual_id, text)")
    parser.add_argument("--out", "-o", type=Path, default=None, help="Output path (default: overwrite --train)")
    parser.add_argument("--audit", "-a", type=Path, default=None, help="Audit JSON path (default: data/clean_contrastive_audit.json)")
    parser.add_argument("--dry-run", action="store_true", help="Do not write files")
    args = parser.parse_args()

    out_path = args.out or args.train
    audit_path = args.audit or (args.train.parent / "clean_contrastive_audit.json")
    try:
        run(args.train, args.corpus, out_path=out_path, audit_path=audit_path, dry_run=args.dry_run)
    except Exception as e:
        logger.exception("%s", e)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
