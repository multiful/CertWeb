"""
Current RAG(웹 실제) vs RRF_Only(평가 파이프라인) 쿼리별 결과 비교.

contrastive_profile_train_example.json에서 raw_query + profile을 읽어,
동일 쿼리에 대해 Current(API 응답)와 RRF_Only(hybrid_retrieve) 상위 N개를 나란히 출력.

출력 JSON 스키마 (--out 지정 시):
  - queries: [{ query_id, raw_query, major, expected: [{qual_id, qual_name}],
                current_top_n: [{qual_id, qual_name, reason?, hybrid_score, rrf_score?}],
                rrf_only_top_n: [{qual_id, qual_name, score}],
                hit_at_n_current, hit_at_n_rrf }]
  - summary: { total, current_errors, rrf_errors }

API 5xx 시 Current는 prod_rrf(vector+tsvector RRF만) fallback으로 채움 (_fallback: "prod_rrf").

실행 (cert-app/backend, PYTHONPATH=backend 또는 uv run):
  uv run python scripts/compare_current_vs_rrf_queries.py --input data/contrastive_profile_train_example.json
  uv run python scripts/compare_current_vs_rrf_queries.py --input data/contrastive_profile_train_example.json --max-queries 5 --out data/compare_current_rrf_result.json
"""
import argparse
import json
import sys
from pathlib import Path

# backend 루트를 path에 넣어 app 임포트 가능하게 (스크립트는 cert-app/backend에서 실행)
_backend = Path(__file__).resolve().parents[1]
if str(_backend) not in sys.path:
    sys.path.insert(0, str(_backend))

from sqlalchemy import text
from fastapi.testclient import TestClient

from app.database import SessionLocal, get_db
from main import app  # 백엔드 루트의 main.py
from app.api.deps import check_rate_limit, get_optional_user
from app.rag.retrieve.hybrid import hybrid_retrieve

# TestClient용 의존성 오버라이드: DB 세션, 레이트리밋 스킵, 비로그인
def _override_deps():
    def override_get_db():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    def noop_rate_limit():
        return None

    def noop_optional_user():
        return None

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[check_rate_limit] = noop_rate_limit
    app.dependency_overrides[get_optional_user] = noop_optional_user


def _get_expected_positives(row: dict) -> list:
    """한 row에서 기대 정답 리스트 (qual_id, qual_name) 추출. positive 단일 / positives 복수 호환."""
    if "positives" in row and row["positives"]:
        return [(p.get("qual_id"), p.get("qual_name")) for p in row["positives"]]
    if "positive" in row and row["positive"]:
        p = row["positive"]
        return [(p.get("qual_id"), p.get("qual_name"))]
    return []


def _qual_name_to_qual_id(db, qual_name: str) -> int | None:
    """qual_name으로 현재 DB의 qual_id 조회 (contrastive README: JSON qual_id와 DB가 다를 수 있음)."""
    if not qual_name or not (qual_name := qual_name.strip()):
        return None
    try:
        row = db.execute(
            text("SELECT qual_id FROM qualification WHERE TRIM(qual_name) = :name LIMIT 1"),
            {"name": qual_name},
        ).fetchone()
        if row:
            return int(row[0])
        row = db.execute(
            text("SELECT qual_id FROM qualification WHERE qual_name ILIKE :pat LIMIT 1"),
            {"pat": f"%{qual_name}%"},
        ).fetchone()
        if row:
            return int(row[0])
    except Exception:
        pass
    return None


def _expected_names_to_db_qual_ids(db, expected: list) -> set:
    """기대 정답 (qual_id, qual_name) 리스트를 현재 DB qual_id 집합으로 변환. qual_name 우선 조회."""
    out = set()
    for qid, name in expected:
        if name and (resolved := _qual_name_to_qual_id(db, name)):
            out.add(resolved)
        elif qid is not None:
            out.add(int(qid))
    return out


def _chunk_id_to_qual_id(chunk_id: str) -> int:
    """chunk_id 'qual_id:chunk_index' -> qual_id."""
    try:
        return int(chunk_id.split(":")[0])
    except (ValueError, IndexError):
        return 0


def _fetch_qual_names(db, qual_ids: list) -> dict:
    """qual_id -> qual_name 매핑 (DB)."""
    if not qual_ids:
        return {}
    rows = db.execute(
        text("SELECT qual_id, qual_name FROM qualification WHERE qual_id = ANY(:ids)"),
        {"ids": list(qual_ids)},
    ).fetchall()
    return {int(r.qual_id): (r.qual_name or "") for r in rows}


def fetch_current_rag_results(major: str, interest: str, limit: int = 10, db=None) -> list:
    """
    Current RAG: API hybrid-recommendation 호출 (TestClient).
    실패 시(5xx/4xx) prod_rrf(vector+tsvector RRF만) fallback으로 동일 쿼리 상위 N개 반환.
    반환: [{"qual_id": int, "qual_name": str, "reason": str, "hybrid_score": float, "rrf_score": float | None}, ...]
    """
    _override_deps()
    client = TestClient(app)
    try:
        resp = client.get(
            "/api/v1/recommendations/ai/hybrid-recommendation",
            params={"major": major, "interest": interest or None, "limit": limit},
            headers={"Host": "localhost"},
        )
    except Exception as e:
        if db is not None:
            return _fetch_prod_rrf_fallback(db, interest or major, limit)
        return [{"_error": str(e)}]
    if resp.status_code != 200:
        if db is not None and resp.status_code >= 500:
            return _fetch_prod_rrf_fallback(db, interest or major, limit)
        return [{"_error": f"HTTP {resp.status_code}", "_body": resp.text[:500]}]
    data = resp.json()
    results = data.get("results") or []
    out = []
    for r in results:
        out.append({
            "qual_id": r.get("qual_id"),
            "qual_name": r.get("qual_name") or "",
            "reason": (r.get("reason") or "")[:200],
            "hybrid_score": r.get("hybrid_score"),
            "rrf_score": r.get("rrf_score"),
        })
    return out


def _prod_rrf_top_k(db, query: str, k: int) -> list:
    """
    웹과 동일한 vector + tsvector RRF만 수행 (prod_rrf).
    반환: [(chunk_id, score), ...] 상위 k개.
    """
    from app.rag.config import get_rag_settings
    from app.rag.utils.dense_query_rewrite import rewrite_for_dense
    from app.rag.index.vector_index import get_vector_search
    RRF_K = 60
    q = (query or "").strip()
    base = q
    if "정보처리기사" in q:
        base = "정보처리기사 정보처리"
    elif q.upper() == "SQL" or "SQL" in q:
        base = "SQL 데이터베이스"
    elif "간호" in q:
        base = "간호사 간호"
    settings = get_rag_settings()
    vector_query = q
    if getattr(settings, "RAG_DENSE_USE_QUERY_REWRITE", True):
        try:
            rewritten = rewrite_for_dense(q, profile=None)
            if rewritten and rewritten.strip():
                vector_query = rewritten
        except Exception:
            pass
    vec_list = get_vector_search(
        db, vector_query, top_k=k * 2,
        threshold=getattr(settings, "RAG_VECTOR_THRESHOLD", 0.25),
        use_rewrite=False,
    )
    try:
        ft_sql = text("""
            SELECT qual_id, COALESCE(chunk_index, 0) AS chunk_index,
                   ts_rank_cd(content_tsv, plainto_tsquery('simple', :q)) AS rank
            FROM certificates_vectors
            WHERE content_tsv @@ plainto_tsquery('simple', :q)
            ORDER BY rank DESC
            LIMIT :limit
        """)
        rows = db.execute(ft_sql, {"q": base, "limit": k * 2}).fetchall()
        fts_list = [(f"{r.qual_id}:{getattr(r, 'chunk_index', 0)}", float(getattr(r, "rank", 0))) for r in rows]
    except Exception:
        db.rollback()
        fts_list = []
    if not vec_list and not fts_list:
        return []
    if not fts_list:
        return vec_list[:k]
    if not vec_list:
        return fts_list[:k]
    tokens = q.split()
    is_keywordy = len(tokens) <= 2 and len(q) <= 8 or any(s in q for s in ["기사", "산업기사", "기능사"]) or q.upper() == "SQL" or "컴퓨터" in q
    w_d, w_s = (1.0, 1.2) if is_keywordy else (1.3, 0.7)
    rank_v = {cid: i + 1 for i, (cid, _) in enumerate(vec_list)}
    rank_t = {cid: i + 1 for i, (cid, _) in enumerate(fts_list)}
    all_cids = set(rank_v) | set(rank_t)
    rrf_scores = []
    for cid in all_cids:
        rv, rt = rank_v.get(cid, 9999), rank_t.get(cid, 9999)
        rrf_scores.append((cid, w_d * (1.0 / (RRF_K + rv)) + w_s * (1.0 / (RRF_K + rt))))
    rrf_scores.sort(key=lambda x: -x[1])
    return rrf_scores[:k]


def _fetch_prod_rrf_fallback(db, query: str, top_k: int) -> list:
    """API 실패 시 웹과 동일한 vector+tsvector RRF만 사용 (prod_rrf)."""
    try:
        pairs = _prod_rrf_top_k(db, query, top_k * 2)
    except Exception:
        return []
    seen = set()
    unique = []
    for chunk_id, score in pairs:
        qid = _chunk_id_to_qual_id(chunk_id)
        if qid and qid not in seen:
            seen.add(qid)
            unique.append((qid, score))
        if len(unique) >= top_k:
            break
    if not unique:
        return []
    qual_ids = [qid for qid, _ in unique[:top_k]]
    names = _fetch_qual_names(db, qual_ids)
    return [
        {"qual_id": qid, "qual_name": names.get(qid, ""), "score": score, "hybrid_score": score, "_fallback": "prod_rrf"}
        for qid, score in unique[:top_k]
    ]


def fetch_rrf_only_results(db, query: str, top_k: int = 10) -> list:
    """
    RRF_Only: hybrid_retrieve(use_reranker=False). chunk_id -> qual_id 유지, qual_id 기준 첫 등장 순위로 상위 top_k.
    반환: [{"qual_id": int, "qual_name": str, "score": float}, ...]
    """
    try:
        pairs = hybrid_retrieve(db, query, top_k=top_k * 2, use_reranker=False)
    except Exception as e:
        return [{"_error": str(e)}]
    # qual_id 기준 첫 등장(최고 순위)만 유지
    seen = set()
    unique = []
    for chunk_id, score in pairs:
        qid = _chunk_id_to_qual_id(chunk_id)
        if qid and qid not in seen:
            seen.add(qid)
            unique.append((qid, score))
        if len(unique) >= top_k:
            break
    if not unique:
        return []
    qual_ids = [qid for qid, _ in unique]
    names = _fetch_qual_names(db, qual_ids)
    return [
        {"qual_id": qid, "qual_name": names.get(qid, ""), "score": score}
        for qid, score in unique[:top_k]
    ]


def run_compare(
    input_path: str,
    max_queries: int | None = 10,
    top_n: int = 10,
    out_path: str | None = None,
) -> dict:
    with open(input_path, "r", encoding="utf-8") as f:
        rows = json.load(f)
    if not isinstance(rows, list):
        rows = [rows]
    if max_queries and max_queries > 0:
        rows = rows[:max_queries]

    report = {"queries": [], "summary": {"total": len(rows), "current_errors": 0, "rrf_errors": 0}}
    db = SessionLocal()
    try:
        for i, row in enumerate(rows):
            raw_query = (row.get("raw_query") or "").strip()
            profile = row.get("profile") or {}
            major = (profile.get("major") or "").strip() or "산업데이터공학"
            query_id = row.get("query_id") or f"q{i+1}"

            expected = _get_expected_positives(row)
            # contrastive README: 골든은 qual_name으로 DB qual_id를 조회해 사용 (JSON qual_id가 다른 DB일 수 있음)
            expected_ids = _expected_names_to_db_qual_ids(db, expected)

            current_results = fetch_current_rag_results(major, raw_query, limit=top_n, db=db)
            if current_results and isinstance(current_results[0].get("_error"), str):
                report["summary"]["current_errors"] += 1
            rrf_results = fetch_rrf_only_results(db, raw_query, top_k=top_n)
            if rrf_results and isinstance(rrf_results[0].get("_error"), str):
                report["summary"]["rrf_errors"] += 1

            # Hit@top_n: 기대 정답이 상위 N개 안에 몇 개 포함되는지
            current_ids = [r["qual_id"] for r in current_results if r.get("qual_id") and "_error" not in r]
            rrf_ids = [r["qual_id"] for r in rrf_results if r.get("qual_id") and "_error" not in r]
            hit_current = len(expected_ids & set(current_ids[:top_n]))
            hit_rrf = len(expected_ids & set(rrf_ids[:top_n]))

            report["queries"].append({
                "query_id": query_id,
                "raw_query": raw_query,
                "major": major,
                "expected": [{"qual_id": e[0], "qual_name": e[1]} for e in expected],
                "current_top_n": current_results,
                "rrf_only_top_n": rrf_results,
                "hit_at_n_current": hit_current,
                "hit_at_n_rrf": hit_rrf,
            })
    finally:
        db.close()

    if out_path:
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
    return report


def main():
    parser = argparse.ArgumentParser(description="Current RAG vs RRF_Only 쿼리별 결과 비교")
    parser.add_argument("--input", "-i", default="data/contrastive_profile_train_example.json", help="contrastive JSON 경로")
    parser.add_argument("--max-queries", "-n", type=int, default=10, help="처리할 쿼리 수 (0이면 전부)")
    parser.add_argument("--top-n", type=int, default=10, help="상위 N개 추천")
    parser.add_argument("--out", "-o", default=None, help="결과 JSON 저장 경로")
    args = parser.parse_args()
    max_q = args.max_queries if args.max_queries > 0 else None
    report = run_compare(args.input, max_queries=max_q, top_n=args.top_n, out_path=args.out)
    print("Summary:", report["summary"])
    if args.out:
        print("Wrote:", args.out)
    for q in report["queries"][:3]:
        print(f"\n[{q['query_id']}] {q['raw_query'][:50]}...")
        print("  expected:", [e["qual_name"] for e in q["expected"]])
        print("  current hit@n:", q["hit_at_n_current"], "| names:", [r.get("qual_name") for r in q["current_top_n"][:5] if r.get("qual_name")])
        print("  rrf_only hit@n:", q["hit_at_n_rrf"], "| names:", [r.get("qual_name") for r in q["rrf_only_top_n"][:5] if r.get("qual_name")])
    if len(report["queries"]) > 3:
        print("\n... (see full output in --out file)")


if __name__ == "__main__":
    main()
