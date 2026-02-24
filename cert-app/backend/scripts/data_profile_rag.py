"""
RAG/벡터 데이터 프로파일링 (MLOps Data Profiler 기준).

단계: Load → Validate → Profile. 
- qualification, certificates_vectors 행 수·길이 분포·임베딩 유무·이상치 요약.
- 반복 연산 회피, 스키마 검증 관점 요약.
실행: cert-app/backend 에서 uv run python scripts/data_profile_rag.py
"""
import os
import sys

# backend 루트를 path에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from app.database import SessionLocal


def profile_certificates_vectors(db) -> dict:
    """certificates_vectors 테이블 프로파일: 행 수, content 길이 분포, embedding 유무."""
    out = {"table": "certificates_vectors", "rows": 0, "content_length": {}, "embedding_null": 0}
    try:
        n = db.execute(text("SELECT COUNT(*) FROM certificates_vectors")).scalar() or 0
        out["rows"] = n
        if n == 0:
            return out
        # 길이 분포 (벡터화: DB에서 한 번에)
        row = db.execute(text("""
            SELECT
                MIN(LENGTH(content)) AS min_len,
                MAX(LENGTH(content)) AS max_len,
                AVG(LENGTH(content))::float AS avg_len,
                PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY LENGTH(content)) AS median_len
            FROM certificates_vectors
        """)).fetchone()
        if row:
            out["content_length"] = {
                "min": row.min_len,
                "max": row.max_len,
                "avg": round(row.avg_len, 1) if row.avg_len is not None else None,
                "median": row.median_len,
            }
        null_emb = db.execute(text("SELECT COUNT(*) FROM certificates_vectors WHERE embedding IS NULL")).scalar() or 0
        out["embedding_null"] = null_emb
    except Exception as e:
        out["error"] = str(e)
    return out


def profile_qualification(db) -> dict:
    """qualification 테이블 프로파일: 행 수, qual_name 길이, embedding 유무."""
    out = {"table": "qualification", "rows": 0, "qual_name_length": {}, "embedding_null": None}
    try:
        n = db.execute(text("SELECT COUNT(*) FROM qualification")).scalar() or 0
        out["rows"] = n
        if n == 0:
            return out
        # qual_name 길이 분포
        try:
            row = db.execute(text("""
                SELECT
                    MIN(LENGTH(qual_name)) AS min_len,
                    MAX(LENGTH(qual_name)) AS max_len,
                    AVG(LENGTH(qual_name))::float AS avg_len
                FROM qualification
            """)).fetchone()
            if row and row.max_len is not None:
                out["qual_name_length"] = {
                    "min": row.min_len,
                    "max": row.max_len,
                    "avg": round(row.avg_len, 1) if row.avg_len is not None else None,
                }
        except Exception:
            pass
        try:
            null_emb = db.execute(text("SELECT COUNT(*) FROM qualification WHERE embedding IS NULL")).scalar()
            out["embedding_null"] = null_emb
        except Exception:
            out["embedding_null"] = "N/A (column may not exist)"
    except Exception as e:
        out["error"] = str(e)
    return out


def print_report(cv: dict, q: dict) -> None:
    """프로파일 결과를 읽기 쉽게 출력."""
    print("=" * 60)
    print("RAG 데이터 프로파일 (MLOps Data Profiler 기준)")
    print("=" * 60)

    print("\n[1] certificates_vectors (청크/벡터 저장소)")
    print(f"  - 행 수: {cv.get('rows', 0)}")
    if cv.get("error"):
        print(f"  - 오류: {cv['error']}")
    else:
        cl = cv.get("content_length") or {}
        if cl:
            print(f"  - content 길이: min={cl.get('min')}, max={cl.get('max')}, avg={cl.get('avg')}, median={cl.get('median')}")
        if cv.get("embedding_null", 0) > 0:
            print(f"  - embedding NULL 개수: {cv['embedding_null']} (이상치: 임베딩 누락)")

    print("\n[2] qualification (자격증 마스터)")
    print(f"  - 행 수: {q.get('rows', 0)}")
    if q.get("error"):
        print(f"  - 오류: {q['error']}")
    else:
        ql = q.get("qual_name_length") or {}
        if ql:
            print(f"  - qual_name 길이: min={ql.get('min')}, max={ql.get('max')}, avg={ql.get('avg')}")
        if q.get("embedding_null") is not None:
            print(f"  - embedding NULL 개수: {q['embedding_null']}")

    print("\n[3] 검토 요약 (스킬 체크리스트)")
    print("  - 벡터화: 프로파일링 쿼리는 집계 1회로 row-wise loop 없음.")
    print("  - 스키마: certificates_vectors(qual_id,name,content,embedding,metadata); qualification(qual_id,qual_name,...,embedding).")
    print("  - 이상치: content/qual_name 길이 0 또는 극단적 max 값은 수동 확인 권장.")
    print("  - AI 추론: app.utils.ai 에서 embedding 호출 시 latency_ms, input_tokens 로깅 적용됨.")
    print("=" * 60)


def main() -> None:
    db = SessionLocal()
    try:
        cv = profile_certificates_vectors(db)
        q = profile_qualification(db)
        print_report(cv, q)
    finally:
        db.close()


if __name__ == "__main__":
    main()
