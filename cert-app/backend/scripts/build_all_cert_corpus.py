#!/usr/bin/env python3
"""
전체 자격증 코퍼스(ALL_CERT_CORPUS_JSON) 생성 스크립트.

- 모드 A (--from-train-json): contrastive 학습 데이터셋에서 임시 코퍼스 추출
  → positive/positives/negatives 수집, qual_name 기준 dedupe, all_cert_corpus_from_train.json
- 모드 B (--from-master-json / --from-master-csv): 실제 전체 자격증 목록(JSON/CSV)에서 최종 코퍼스 생성
  → retrieval 평가용 all_cert_corpus.json

출력 형식 통일: [ {"qual_id": ..., "qual_name": "...", "text": "..."}, ... ]
"""
from __future__ import annotations

import argparse
import csv
import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

# UTF-8 기본 설정
if sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


# ---------- JSON 루트 검증 ----------


def validate_json_root(data: Any) -> List[Any]:
    """JSON 루트가 배열인지 검증 후 반환. 아니면 예외."""
    if data is None:
        raise ValueError("JSON root is null")
    if not isinstance(data, list):
        raise ValueError(f"JSON root must be an array, got {type(data).__name__}")
    return data


# ---------- 학습 데이터셋 → 임시 코퍼스 (작업 A) ----------


def _normalize_qual_name(name: Any) -> str:
    return (str(name or "").strip() or "").strip()


def _extract_doc(item: Dict[str, Any], source_role: str) -> Optional[Dict[str, Any]]:
    """단일 positive/negative 항목에서 qual_id, qual_name, text 추출. 유효하지 않으면 None."""
    qual_name = _normalize_qual_name(item.get("qual_name"))
    if not qual_name:
        return None
    text = (item.get("text") or "").strip()
    # text가 비어 있어도 qual_name만으로 문서로 쓸 수 있게 허용 (최소 텍스트 생성)
    if not text:
        text = f"자격증명: {qual_name}"
    qual_id = item.get("qual_id")
    if qual_id is not None and not isinstance(qual_id, int):
        try:
            qual_id = int(qual_id)
        except (TypeError, ValueError):
            qual_id = None
    return {
        "qual_id": qual_id,
        "qual_name": qual_name,
        "text": text,
        "_source_role": source_role,
    }


def _collect_from_row(row: Dict[str, Any]) -> List[Dict[str, Any]]:
    """한 row에서 positive / positives / negatives 수집. 중복 키는 유지 (나중에 dedupe)."""
    out: List[Dict[str, Any]] = []

    # 단일 positive
    pos = row.get("positive")
    if pos and isinstance(pos, dict):
        doc = _extract_doc(pos, "positive")
        if doc:
            out.append(doc)

    # positives (배열)
    positives = row.get("positives")
    if positives and isinstance(positives, list):
        for p in positives:
            if isinstance(p, dict):
                doc = _extract_doc(p, "positive")
                if doc:
                    out.append(doc)

    # negatives
    negatives = row.get("negatives")
    if negatives and isinstance(negatives, list):
        for n in negatives:
            if isinstance(n, dict):
                doc = _extract_doc(n, "negative")
                if doc:
                    out.append(doc)

    return out


def _merge_duplicate_by_qual_name(
    docs: List[Dict[str, Any]],
    prefer_longer_text: bool = True,
    include_source_roles: bool = False,
) -> List[Dict[str, Any]]:
    """
    qual_name 기준 dedupe. 동일 qual_name이면:
    - prefer_longer_text: True면 더 긴 text를 가진 항목 유지
    - source_roles는 positive/negative를 합쳐서 optional 메타로 남김
    """
    by_name: Dict[str, Dict[str, Any]] = {}
    for d in docs:
        name = _normalize_qual_name(d.get("qual_name"))
        if not name:
            continue
        existing = by_name.get(name)
        if existing is None:
            entry = {
                "qual_id": d.get("qual_id"),
                "qual_name": name,
                "text": (d.get("text") or "").strip(),
            }
            if include_source_roles:
                entry["source_roles"] = [d.get("_source_role", "unknown")]
            by_name[name] = entry
            continue
        # 병합: 더 긴(또는 더 많은 정보) text 선택
        new_text = (d.get("text") or "").strip()
        cur_text = existing.get("text") or ""
        if prefer_longer_text and len(new_text) > len(cur_text):
            existing["text"] = new_text
            if existing.get("qual_id") is None and d.get("qual_id") is not None:
                existing["qual_id"] = d.get("qual_id")
        elif not prefer_longer_text and len(new_text) > 0 and len(cur_text) == 0:
            existing["text"] = new_text
            if existing.get("qual_id") is None and d.get("qual_id") is not None:
                existing["qual_id"] = d.get("qual_id")
        if include_source_roles and d.get("_source_role"):
            roles = existing.setdefault("source_roles", [])
            if d.get("_source_role") not in roles:
                roles.append(d.get("_source_role"))
    result = []
    for v in by_name.values():
        if include_source_roles and "source_roles" in v:
            pass  # 유지
        else:
            v.pop("source_roles", None)
        v.pop("_source_role", None)
        result.append({k: v[k] for k in ("qual_id", "qual_name", "text") if k in v})
        if include_source_roles and "source_roles" in v:
            result[-1]["source_roles"] = v["source_roles"]
    return result


def build_corpus_from_train_json(
    input_path: Path,
    output_path: Path,
    include_source_roles: bool = False,
    prefer_longer_text: bool = True,
) -> int:
    """
    contrastive 학습 JSON에서 자격증 문서만 추출해 qual_name 기준 dedupe 후 저장.
    반환: 저장된 문서 수.
    """
    logger.info("학습 데이터셋에서 코퍼스 추출: %s", input_path)
    try:
        with open(input_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        logger.error("파일 없음: %s", input_path)
        raise
    except json.JSONDecodeError as e:
        logger.error("JSON 파싱 실패: %s", e)
        raise

    rows = validate_json_root(data)
    collected: List[Dict[str, Any]] = []
    for i, row in enumerate(rows):
        if not isinstance(row, dict):
            logger.warning("row %s is not a dict, skip", i)
            continue
        collected.extend(_collect_from_row(row))

    logger.info("수집된 문서 수(중복 포함): %s", len(collected))
    corpus = _merge_duplicate_by_qual_name(
        collected,
        prefer_longer_text=prefer_longer_text,
        include_source_roles=include_source_roles,
    )
    logger.info("qual_name dedupe 후 문서 수: %s", len(corpus))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(corpus, f, ensure_ascii=False, indent=2)

    logger.info("저장 완료: %s", output_path)
    return len(corpus)


# ---------- 마스터 JSON/CSV → 최종 코퍼스 (작업 B) ----------


# 마스터 행에서 retrieval용 text 필드 구성 시 사용할 키 후보 (우선순위 순)
TEXT_FIELD_KEYS = {
    "자격증명": ["qual_name", "qual_name", "자격증명"],
    "자격종류": ["qual_type", "qual_type", "자격종류", "유형"],
    "관련직무": ["related_jobs", "jobs", "main_field", "관련직무", "ncs_large"],
    "추천대상": ["target_audience", "recommendation_target", "추천대상"],
    "설명": ["description", "desc", "설명", "main_field"],
}


def _get_first_nonempty(row: Dict[str, Any], keys: List[str]) -> str:
    for k in keys:
        v = row.get(k)
        if v is not None and str(v).strip():
            return str(v).strip()
    return ""


def build_text_from_master_row(row: Dict[str, Any]) -> str:
    """
    마스터 한 행(JSON/CSV row)을 retrieval용 구조화 텍스트로 변환.
    자격증명 / 자격종류 / 관련직무 / 추천대상 / 설명 포맷을 최대한 맞춤.
    """
    lines: List[str] = []
    name = _get_first_nonempty(row, ["qual_name", "자격증명"])
    if name:
        lines.append(f"자격증명: {name}")
    kind = _get_first_nonempty(row, list(TEXT_FIELD_KEYS["자격종류"]))
    if kind:
        lines.append(f"자격종류: {kind}")
    jobs = _get_first_nonempty(row, list(TEXT_FIELD_KEYS["관련직무"]))
    if jobs:
        lines.append(f"관련직무: {jobs}")
    target = _get_first_nonempty(row, list(TEXT_FIELD_KEYS["추천대상"]))
    if target:
        lines.append(f"추천대상: {target}")
    desc = _get_first_nonempty(row, list(TEXT_FIELD_KEYS["설명"]))
    if not desc:
        # fallback: main_field + qual_type 등으로 설명 구성
        parts = [
            row.get("main_field"),
            row.get("qual_type"),
            row.get("ncs_large"),
            row.get("managing_body"),
        ]
        desc = " ".join(str(p).strip() for p in parts if p).strip()
    if desc:
        lines.append(f"설명: {desc}")
    if not lines:
        lines.append(f"자격증명: {name or '자격증'}")
    return "\n".join(lines)


def load_master_json(input_path: Path) -> List[Dict[str, Any]]:
    """JSON 파일 로드. 루트가 배열이어야 함."""
    with open(input_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return validate_json_root(data)


def load_master_csv(input_path: Path, delimiter: str = ",") -> List[Dict[str, Any]]:
    """CSV 파일 로드. 첫 행을 헤더로 사용."""
    rows: List[Dict[str, Any]] = []
    with open(input_path, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f, delimiter=delimiter)
        for r in reader:
            # 빈 행 스킵
            if not any(str(v).strip() for v in r.values()):
                continue
            rows.append(r)
    return rows


def build_corpus_from_rows(
    rows: List[Dict[str, Any]],
    output_path: Path,
    dedupe_by: str = "qual_name",
) -> int:
    """
    마스터와 동일한 형식의 행 리스트에서 코퍼스 생성.
    (JSON/CSV/DB 등 어떤 소스에서든 rows만 맞추면 재사용 가능)
    """
    logger.info("행 수: %s", len(rows))
    seen: Set[str] = set()
    corpus: List[Dict[str, Any]] = []
    for r in rows:
        if not isinstance(r, dict):
            continue
        qual_name = _normalize_qual_name(_get_first_nonempty(r, ["qual_name", "자격증명"]))
        if not qual_name:
            logger.debug("qual_name 없음 행 스킵: %s", list(r.keys())[:5])
            continue
        qual_id = r.get("qual_id")
        if qual_id is not None and not isinstance(qual_id, int):
            try:
                qual_id = int(qual_id)
            except (TypeError, ValueError):
                qual_id = None
        # DB에서 이미 가져온 text(certificates_vectors content)가 있으면 사용
        text = (r.get("text") or "").strip() or build_text_from_master_row(r)
        if not text.strip():
            text = f"자격증명: {qual_name}"

        key = qual_name if dedupe_by == "qual_name" else (str(qual_id) if qual_id is not None else qual_name)
        if dedupe_by != "none" and key in seen:
            continue
        seen.add(key)
        corpus.append({"qual_id": qual_id, "qual_name": qual_name, "text": text})

    logger.info("최종 코퍼스 문서 수: %s", len(corpus))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(corpus, f, ensure_ascii=False, indent=2)
    logger.info("저장 완료: %s", output_path)
    return len(corpus)


def load_master_from_db(use_vectors_content: bool = True) -> List[Dict[str, Any]]:
    """
    Supabase(PostgreSQL) qualification 테이블에서 전체 자격증을 읽어 마스터 행 리스트로 반환.
    - is_active 필터 없이 전체 조회 (자격증 1103개 등 전체 후보).
    - use_vectors_content=True이면 certificates_vectors에서 qual_id별 chunk_index=0 content를
      가져와 text로 사용(실제 검색 인덱스와 동일). 없으면 qualification 컬럼으로 text 생성.
    """
    try:
        from sqlalchemy import text as sql_text
        from app.database import SessionLocal
        from app.models import Qualification
    except ImportError as e:
        logger.error("DB 로드 시 import 실패 (backend 경로에서 실행 필요): %s", e)
        raise
    db = SessionLocal()
    try:
        # 전체 자격증 (Supabase qualification 테이블, 필터 없음)
        quals = db.query(Qualification).order_by(Qualification.qual_id).all()
        logger.info("qualification 테이블 조회: %s건", len(quals))

        # optional: certificates_vectors에서 qual_id별 대표 content (chunk_index=0)
        content_by_qual_id: Dict[int, str] = {}
        if use_vectors_content and quals:
            try:
                qual_ids = [q.qual_id for q in quals]
                # chunk_index 0 또는 NULL인 행만 (자격증 1개당 1문서)
                rows = db.execute(
                    sql_text("""
                        SELECT qual_id, COALESCE(content, '') AS content
                        FROM certificates_vectors
                        WHERE qual_id = ANY(:ids)
                          AND (chunk_index = 0 OR chunk_index IS NULL)
                    """),
                    {"ids": qual_ids},
                ).fetchall()
                for r in rows:
                    qid = getattr(r, "qual_id", None)
                    content = (getattr(r, "content", None) or "").strip()
                    if qid is not None and content:
                        content_by_qual_id[int(qid)] = content
                logger.info("certificates_vectors에서 content 로드: %s건", len(content_by_qual_id))
            except Exception as e:
                logger.warning("certificates_vectors 조회 실패, qualification 기준으로 text 생성: %s", e)

        out = []
        for q in quals:
            row = {
                "qual_id": q.qual_id,
                "qual_name": q.qual_name or "",
                "qual_type": q.qual_type or "",
                "main_field": q.main_field or "",
                "ncs_large": q.ncs_large or "",
                "managing_body": q.managing_body or "",
                "grade_code": q.grade_code or "",
            }
            if q.qual_id in content_by_qual_id:
                row["text"] = content_by_qual_id[q.qual_id]
            out.append(row)
        return out
    finally:
        db.close()


def build_corpus_from_master(
    input_path: Path,
    output_path: Path,
    format_type: str = "json",
    csv_delimiter: str = ",",
    dedupe_by: str = "qual_name",
) -> int:
    """
    마스터 JSON 또는 CSV 파일에서 전체 자격증 코퍼스 생성.
    format_type: "json" | "csv"
    dedupe_by: "qual_name" (기본) | "qual_id" | "none"
    반환: 저장된 문서 수.
    """
    logger.info("마스터 %s에서 코퍼스 생성: %s", format_type.upper(), input_path)
    if format_type == "json":
        rows = load_master_json(input_path)
    elif format_type == "csv":
        rows = load_master_csv(input_path, delimiter=csv_delimiter)
    else:
        raise ValueError(f"Unsupported format: {format_type}")
    return build_corpus_from_rows(rows, output_path, dedupe_by=dedupe_by)


# ---------- CLI ----------


def main() -> int:
    parser = argparse.ArgumentParser(
        description="전체 자격증 코퍼스(ALL_CERT_CORPUS) 생성: 학습 데이터셋 또는 마스터 JSON/CSV 기반.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--from-train-json",
        type=Path,
        metavar="PATH",
        help="contrastive 학습 데이터셋 JSON 경로 → 임시 코퍼스 생성 (작업 A)",
    )
    parser.add_argument(
        "--from-master-json",
        type=Path,
        metavar="PATH",
        help="전체 자격증 마스터 JSON 경로 → 최종 코퍼스 생성 (작업 B)",
    )
    parser.add_argument(
        "--from-master-csv",
        type=Path,
        metavar="PATH",
        help="전체 자격증 마스터 CSV 경로 → 최종 코퍼스 생성 (작업 B)",
    )
    parser.add_argument(
        "--from-db",
        action="store_true",
        help="Supabase(PostgreSQL) qualification 테이블에서 전체 자격증 로드 → 최종 코퍼스 (작업 B, 1103건)",
    )
    parser.add_argument(
        "--no-vectors-content",
        action="store_true",
        help="--from-db 시 certificates_vectors content 미사용, qualification 컬럼만으로 text 생성",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        metavar="PATH",
        help="출력 JSON 경로. 미지정 시 모드별 기본값 사용.",
    )
    parser.add_argument(
        "--no-source-roles",
        action="store_true",
        help="(train 모드) source_roles 메타데이터 제외",
    )
    parser.add_argument(
        "--master-csv-delimiter",
        type=str,
        default=",",
        metavar="CHAR",
        help="--from-master-csv 사용 시 구분자",
    )
    parser.add_argument(
        "--dedupe-by",
        type=str,
        choices=("qual_name", "qual_id", "none"),
        default="qual_name",
        help="마스터 모드 dedupe 기준",
    )
    args = parser.parse_args()

    mode_count = sum(
        [
            1 if args.from_train_json else 0,
            1 if args.from_master_json else 0,
            1 if args.from_master_csv else 0,
            1 if args.from_db else 0,
        ]
    )
    if mode_count == 0:
        logger.error("--from-train-json, --from-master-json, --from-master-csv, --from-db 중 하나를 지정하세요.")
        return 1
    if mode_count > 1:
        logger.error("한 번에 하나의 모드만 지정하세요.")
        return 1

    try:
        if args.from_train_json:
            out = args.output or Path("data/all_cert_corpus_from_train.json")
            build_corpus_from_train_json(
                args.from_train_json,
                out,
                include_source_roles=not args.no_source_roles,
                prefer_longer_text=True,
            )
        elif args.from_master_json:
            out = args.output or Path("data/all_cert_corpus.json")
            build_corpus_from_master(
                args.from_master_json,
                out,
                format_type="json",
                dedupe_by=args.dedupe_by,
            )
        elif args.from_master_csv:
            out = args.output or Path("data/all_cert_corpus.json")
            build_corpus_from_master(
                args.from_master_csv,
                out,
                format_type="csv",
                csv_delimiter=args.master_csv_delimiter,
                dedupe_by=args.dedupe_by,
            )
        else:
            out = args.output or Path("data/all_cert_corpus.json")
            rows = load_master_from_db(use_vectors_content=not getattr(args, "no_vectors_content", False))
            build_corpus_from_rows(rows, out, dedupe_by=args.dedupe_by)
    except Exception as e:
        logger.exception("실행 오류: %s", e)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
