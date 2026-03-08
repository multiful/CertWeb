#!/usr/bin/env python3
"""
contrastive 학습 JSON의 qual_id를 Supabase 기준으로 맞춤.

all_cert_corpus.json(Supabase export)의 qual_name -> qual_id 매핑을 사용해
contrastive_profile_train_merged.json 내 positive / positives / negatives 의
qual_id를 Supabase qual_id로 치환한다.
- 정확 일치 우선
- 없으면 qual_name 포함 관계로 후보 탐색 (예: "SQLD" -> "SQL개발자(SQLD)")
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def load_corpus_name_to_id(corpus_path: Path) -> Tuple[Dict[str, int], List[Tuple[str, int]]]:
    """all_cert_corpus.json에서 qual_name -> qual_id 매핑 및 (name, id) 목록 반환."""
    with open(corpus_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError("corpus JSON root must be an array")
    name_to_id: Dict[str, int] = {}
    name_id_list: List[Tuple[str, int]] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        name = (item.get("qual_name") or "").strip()
        qid = item.get("qual_id")
        if not name or qid is None:
            continue
        try:
            qid = int(qid)
        except (TypeError, ValueError):
            continue
        name_id_list.append((name, qid))
        if name not in name_to_id:
            name_to_id[name] = qid
    return name_to_id, name_id_list


def resolve_supabase_qual_id(
    train_qual_name: str,
    name_to_id: Dict[str, int],
    name_id_list: List[Tuple[str, int]],
) -> Optional[int]:
    """학습 데이터의 qual_name에 대응하는 Supabase qual_id 반환. 없으면 None."""
    train_n = (train_qual_name or "").strip()
    if not train_n:
        return None
    # 1) 정확 일치
    if train_n in name_to_id:
        return name_to_id[train_n]
    # 2) train 이름이 코퍼스 이름에 포함 (예: SQLD -> SQL개발자(SQLD))
    in_corpus = [(cid, cname) for cname, cid in name_id_list if train_n in cname]
    if in_corpus:
        # 가장 짧은 코퍼스 이름 선택 (가장 구체적일 수 있음)
        return min(in_corpus, key=lambda x: len(x[1]))[0]
    # 3) 코퍼스 이름이 train 이름에 포함
    corpus_in_train = [(cid, cname) for cname, cid in name_id_list if cname in train_n]
    if corpus_in_train:
        return max(corpus_in_train, key=lambda x: len(x[1]))[0]
    return None


def align_row(row: Dict[str, Any], name_to_id: Dict[str, int], name_id_list: List[Tuple[str, int]], stats: Dict[str, int]) -> None:
    """한 row의 positive / positives / negatives 내 qual_id를 Supabase 기준으로 치환 (in-place)."""
    def fix_item(item: Dict[str, Any]) -> None:
        if not isinstance(item, dict):
            return
        name = (item.get("qual_name") or "").strip()
        if not name:
            return
        resolved = resolve_supabase_qual_id(name, name_to_id, name_id_list)
        if resolved is not None:
            old_id = item.get("qual_id")
            if old_id != resolved:
                stats["replaced"] = stats.get("replaced", 0) + 1
            item["qual_id"] = resolved
        else:
            stats["not_found"] = stats.get("not_found", 0) + 1
            # 원본 유지하되 로그는 첫 N건만
            if stats["not_found"] <= 20:
                logger.warning("Supabase에 없음: qual_name=%s", name)

    single = row.get("positive")
    if single and isinstance(single, dict):
        fix_item(single)
    for p in row.get("positives") or []:
        if isinstance(p, dict):
            fix_item(p)
    for n in row.get("negatives") or []:
        if isinstance(n, dict):
            fix_item(n)


def main() -> int:
    parser = argparse.ArgumentParser(description="contrastive 학습 JSON의 qual_id를 Supabase(all_cert_corpus) 기준으로 정렬")
    parser.add_argument("--corpus", type=Path, default=Path("data/all_cert_corpus.json"), help="Supabase 기반 코퍼스 JSON")
    parser.add_argument("--train", type=Path, default=Path("data/contrastive_profile_train_merged.json"), help="학습 JSON")
    parser.add_argument("-o", "--output", type=Path, default=None, help="출력 경로 (미지정 시 train 파일명에 _supabase_ids 붙여 저장)")
    args = parser.parse_args()

    if not args.corpus.exists():
        logger.error("코퍼스 파일 없음: %s", args.corpus)
        return 1
    if not args.train.exists():
        logger.error("학습 JSON 없음: %s", args.train)
        return 1

    name_to_id, name_id_list = load_corpus_name_to_id(args.corpus)
    logger.info("코퍼스 qual_name -> qual_id 매핑: %s건", len(name_to_id))

    with open(args.train, "r", encoding="utf-8") as f:
        train_data = json.load(f)
    if not isinstance(train_data, list):
        logger.error("학습 JSON root는 배열이어야 함")
        return 1

    stats: Dict[str, int] = {}
    for row in train_data:
        if isinstance(row, dict):
            align_row(row, name_to_id, name_id_list, stats)

    out_path = args.output or args.train.parent / (args.train.stem + "_supabase_ids.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(train_data, f, ensure_ascii=False, indent=2)
    logger.info("저장: %s", out_path)
    logger.info("치환=%s, Supabase에 없음=%s", stats.get("replaced", 0), stats.get("not_found", 0))
    return 0


if __name__ == "__main__":
    sys.exit(main())
