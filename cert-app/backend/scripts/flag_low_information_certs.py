"""
2-4: Low-information cert 자동 보강 파이프라인.
정보량이 낮은 자격증을 자동 플래그해 FIELD_TO_JOB_SKILL / alias / dense_content 보강 대상으로 라우팅.

실행: cert-app/backend 에서
  uv run python scripts/flag_low_information_certs.py [--out output.csv] [--limit N]

출력: CSV (qual_id, qual_name, needs_job_skill_boost, needs_alias_boost, needs_dense_review, flags).
"""
import argparse
import csv
import sys
from pathlib import Path
from typing import List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import text

from app.database import SessionLocal

# 상수: populate와 동일한 기준 사용 (스크립트 독립성 위해 복제)
BM25_RECO_PURPOSE_DEFAULT = "취업 실무 입문 자격증 커리어"
FIELD_TO_JOB_SKILL_KEYS = (
    "정보통신", "정보기술개발", "정보처리", "데이터분석", "데이터베이스", "시스템관리",
    "네트워크관리", "정보보안", "전기·전자", "전기설계", "전자개발", "기계", "건설",
    "경제·금융", "보건·의료", "산업데이터공학", "시스템운영", "IT서비스",
)
QUAL_NAME_ALIASES_KEYS = {"정보처리기사", "정보처리산업기사", "빅데이터분석기사", "데이터분석준전문가", "SQL개발자", "네트워크관리사"}

# 기준값
MIN_MAJOR_COUNT = 1
MIN_JOB_SKILL_LEN = 10
MIN_DENSE_CONTENT_LEN = 200


def _has_job_skill_match(main_field: str, ncs_large: str) -> bool:
    """main_field/ncs_large가 FIELD_TO_JOB_SKILL에 매칭되면 True."""
    mf = (main_field or "").strip()
    nc = (ncs_large or "").strip()
    for key in FIELD_TO_JOB_SKILL_KEYS:
        if key in mf or key in nc:
            return True
    return False


def _has_alias(qual_name: str) -> bool:
    """QUAL_NAME_ALIASES에 해당 자격증이 있으면 True."""
    qn = (qual_name or "").replace(" ", "")
    for k in QUAL_NAME_ALIASES_KEYS:
        if k.replace(" ", "") in qn or qn in k.replace(" ", ""):
            return True
    return False


def run(db, limit: Optional[int], out_path: Optional[str]) -> List[dict]:
    """
    DB에서 qualification + major_qualification_map + certificates_vectors 조회 후
    low-information 플래그 부여. 반환: [{"qual_id", "qual_name", "needs_job_skill_boost", ...}, ...]
    """
    # qual_id별 전공 수
    major_counts = {}
    for row in db.execute(text("SELECT qual_id, COUNT(*) AS cnt FROM major_qualification_map GROUP BY qual_id")).fetchall():
        major_counts[row.qual_id] = row.cnt

    # qual_id별 dense_content 길이 (certificates_vectors chunk_index=0 기준 1행)
    dense_len = {}
    try:
        for row in db.execute(text("""
            SELECT qual_id, COALESCE(LENGTH(dense_content), 0) AS len
            FROM certificates_vectors WHERE chunk_index = 0
        """)).fetchall():
            dense_len[row.qual_id] = row.len
    except Exception:
        db.rollback()

    rows = db.execute(text("""
        SELECT qual_id, qual_name, main_field, ncs_large
        FROM qualification
        WHERE is_active = TRUE
        ORDER BY qual_id
    """)).fetchall()

    result = []
    for r in rows:
        qual_id = r.qual_id
        qual_name = (r.qual_name or "").strip()
        main_field = (r.main_field or "").strip()
        ncs_large = (r.ncs_large or "").strip()

        major_empty = major_counts.get(qual_id, 0) < MIN_MAJOR_COUNT
        job_skill_generic = not _has_job_skill_match(main_field, ncs_large) or (len(main_field) + len(ncs_large)) < MIN_JOB_SKILL_LEN
        desc_short = dense_len.get(qual_id, 0) < MIN_DENSE_CONTENT_LEN
        has_alias = _has_alias(qual_name)

        needs_job_skill_boost = major_empty or job_skill_generic
        needs_alias_boost = not has_alias
        needs_dense_review = desc_short

        flags = []
        if major_empty:
            flags.append("major_empty")
        if job_skill_generic:
            flags.append("job_skill_generic")
        if desc_short:
            flags.append("desc_short")
        if not has_alias:
            flags.append("no_alias")

        result.append({
            "qual_id": qual_id,
            "qual_name": qual_name,
            "needs_job_skill_boost": needs_job_skill_boost,
            "needs_alias_boost": needs_alias_boost,
            "needs_dense_review": needs_dense_review,
            "flags": ";".join(flags) if flags else "",
        })
        if limit and len(result) >= limit:
            break

    if out_path:
        with open(out_path, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=["qual_id", "qual_name", "needs_job_skill_boost", "needs_alias_boost", "needs_dense_review", "flags"])
            w.writeheader()
            w.writerows(result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Low-information cert 플래그 (2-4)")
    parser.add_argument("--out", default=None, help="출력 CSV 경로")
    parser.add_argument("--limit", type=int, default=None, help="처리할 최대 qual 수")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        rows = run(db, limit=args.limit, out_path=args.out)
        if not rows:
            print("자격증이 없습니다.")
            return 0
        flagged = [r for r in rows if r["needs_job_skill_boost"] or r["needs_alias_boost"] or r["needs_dense_review"]]
        print(f"총 {len(rows)}건, 보강 대상 플래그: {len(flagged)}건")
        if args.out:
            print(f"저장: {args.out}")
        for r in flagged[:20]:
            print(f"  qual_id={r['qual_id']} {r['qual_name'][:30]} | job_skill={r['needs_job_skill_boost']} alias={r['needs_alias_boost']} dense={r['needs_dense_review']} | {r['flags']}")
        if len(flagged) > 20:
            print(f"  ... 외 {len(flagged) - 20}건")
    finally:
        db.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
