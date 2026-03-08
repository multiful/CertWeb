"""
3축 비교: 베이스라인 RAG vs 현재 RAG(0.4) vs 고도화 RAG(0.3+Hybrid).
- 베이스라인: 벡터(OpenAI)만, 임계값 없음.
- 현재 RAG: 벡터(OpenAI) + 임계값 0.4 (실서비스 설정).
- 고도화 RAG: app.utils.rag_hybrid.enhanced_rag_03_hybrid (가중치 RRF + 다중 질의 Sparse + 경량 리랭커).

실행 (cert-app/backend):
  uv run python scripts/compare_rag_three_way.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text

from app.utils.rag_hybrid import enhanced_rag_03_hybrid

TEST_QUERIES = [
    "정보처리기사",
    "컴퓨터",
    "전기",
    "건축",
    "SQL",
    "간호",
    "산업기사",
    "기사",
]
TOP_K = 10


def get_relevant_qual_ids(db, query: str) -> set:
    """정답 세트: qual_name에 질의어가 포함된 qual_id."""
    rows = db.execute(
        text("""
            SELECT qual_id FROM qualification
            WHERE is_active = TRUE AND qual_name ILIKE :pat
        """),
        {"pat": f"%{query}%"},
    ).fetchall()
    return {r.qual_id for r in rows}


def unique_qual_ids_with_sims(results: list, top_k: int):
    """청크 결과에서 qual_id 유니크 상위 top_k개와 유사도 리스트."""
    seen = set()
    qids, sims = [], []
    for r in results:
        qid = r["qual_id"]
        if qid not in seen:
            seen.add(qid)
            qids.append(qid)
            sims.append(r["similarity"])
        if len(qids) >= top_k:
            break
    return qids[:top_k], sims[:top_k]


def run_three_way(db, test_queries: list, top_k: int):
    """
    베이스라인 / 현재 RAG(0.4) / 고도화 RAG(0.3+Hybrid) 각각
    Recall@10, Precision@10, F1, 저유사도(0.4 미만)% 수집.
    """
    from app.services.vector_service import vector_service
    from app.utils.ai import get_embedding

    fetch_limit = max(top_k * 3, 50)
    keys = ["baseline", "current", "enhanced"]
    results = {k: {"recalls": [], "precisions": [], "f1s": [], "low_sim_04": []} for k in keys}
    results["enhanced"]["low_sim_04"] = None
    for query in test_queries:
        relevant = get_relevant_qual_ids(db, query)
        if len(relevant) == 0:
            continue

        # 1) 베이스라인: 벡터만, 임계값 없음
        res = vector_service.similarity_search(db, query, limit=fetch_limit, match_threshold=None)
        ret, sims = unique_qual_ids_with_sims(res, top_k)
        hits = len(set(ret) & relevant)
        r = hits / len(relevant)
        p = hits / len(ret) if ret else 0
        f1 = 2 * p * r / (p + r) if (p + r) > 0 else 0
        low = sum(1 for s in sims if s < 0.4) / len(sims) * 100 if sims else 0
        results["baseline"]["recalls"].append(r)
        results["baseline"]["precisions"].append(p)
        results["baseline"]["f1s"].append(f1)
        results["baseline"]["low_sim_04"].append(low)

        # 2) 현재 RAG: 벡터 + 임계값 0.4
        res = vector_service.similarity_search(db, query, limit=fetch_limit, match_threshold=0.4)
        ret, sims = unique_qual_ids_with_sims(res, top_k)
        hits = len(set(ret) & relevant)
        r = hits / len(relevant)
        p = hits / len(ret) if ret else 0
        f1 = 2 * p * r / (p + r) if (p + r) > 0 else 0
        low = sum(1 for s in sims if s < 0.4) / len(sims) * 100 if sims else 0
        results["current"]["recalls"].append(r)
        results["current"]["precisions"].append(p)
        results["current"]["f1s"].append(f1)
        results["current"]["low_sim_04"].append(low)

        # 3) 고도화 RAG: 0.3 + Hybrid (OpenAI Dense + content_tsv RRF)
        query_vec = get_embedding(query)
        ret_enh = enhanced_rag_03_hybrid(db, query, query_vec, top_k)
        ret_enh = ret_enh[:top_k]
        hits = len(set(ret_enh) & relevant)
        r = hits / len(relevant)
        p = hits / len(ret_enh) if ret_enh else 0
        f1 = 2 * p * r / (p + r) if (p + r) > 0 else 0
        results["enhanced"]["recalls"].append(r)
        results["enhanced"]["precisions"].append(p)
        results["enhanced"]["f1s"].append(f1)

    return results


def main():
    from app.database import SessionLocal
    from app.config import get_settings

    settings = get_settings()
    if not settings.OPENAI_API_KEY:
        print("OPENAI_API_KEY required for embedding.")
        sys.exit(1)

    db = SessionLocal()
    try:
        print("\n" + "=" * 70)
        print("[질의/정답/검증 정의 및 합당성]")
        print("=" * 70)
        print("질의(검증셋): 8개 고정 쿼리 (정보처리기사, 컴퓨터, 전기, 건축, SQL, 간호, 산업기사, 기사).")
        print("정답: qual_name에 질의어가 포함된 qual_id 를 '관련 있음'으로 정의 (qual_name ILIKE '%query%').")
        print("검증: 동일 쿼리·동일 정답 세트로 각 RAG별 상위 10건을 가져와 Recall@10, Precision@10, F1 계산.")
        print("판단: 일관된 정의로 상대 비교용으로는 합당. 사람 라벨/동의어 반영 없음. 엄밀 평가 시 보강 권장.")
        print("참고: 정보처리기사·SQLD 등 동일 도메인 자격증은 유사도가 비슷해야 한다는 요구는, 리랭커/임베딩")
        print("      튜닝 시 관련 cert 쌍을 비슷하게 두는 제약으로 반영할 수 있음 (본 스크립트는 공통 평가만 수행).")
        print("=" * 70 + "\n")

        results = run_three_way(db, TEST_QUERIES, TOP_K)
        n = len(results["baseline"]["recalls"])
        if n == 0:
            print("No queries with non-empty relevant set.")
            return

        def avg(d, key):
            return sum(d[key]) / len(d[key]) if d[key] else 0

        def row(d, low_none=False):
            r = avg(d, "recalls")
            p = avg(d, "precisions")
            f1 = avg(d, "f1s")
            low = "-" if low_none or d.get("low_sim_04") is None else f"{avg(d, 'low_sim_04'):.1f}%"
            return r, p, f1, low

        print("[3축 비교] 베이스라인 RAG vs 현재 RAG vs 고도화 RAG (동일 8쿼리, 상위 10건)")
        print()
        print(f"{'구분':<28} {'Recall@10':>12} {'Precision@10':>14} {'F1':>10}  {'저유사도(0.4미만)%':>18}")
        print("-" * 86)
        rb = row(results["baseline"])
        print(f"{'베이스라인 RAG (임계값 없음)':<28} {rb[0]:>11.2%} {rb[1]:>13.2%} {rb[2]:>9.2%}  {rb[3]:>18}")
        rc = row(results["current"])
        print(f"{'현재 RAG (임계값 0.4)':<28} {rc[0]:>11.2%} {rc[1]:>13.2%} {rc[2]:>9.2%}  {rc[3]:>18}")
        re = row(results["enhanced"], low_none=True)
        print(f"{'고도화 RAG (0.3+Hybrid)':<28} {re[0]:>11.2%} {re[1]:>13.2%} {re[2]:>9.2%}  {'-':>18}")
        print("-" * 86)

        r_base = avg(results["baseline"], "recalls")
        p_base = avg(results["baseline"], "precisions")
        f_base = avg(results["baseline"], "f1s")
        r_cur = avg(results["current"], "recalls")
        p_cur = avg(results["current"], "precisions")
        f_cur = avg(results["current"], "f1s")
        r_enh = avg(results["enhanced"], "recalls")
        p_enh = avg(results["enhanced"], "precisions")
        f_enh = avg(results["enhanced"], "f1s")

        def chg(new_v, old_v):
            if old_v <= 0:
                return "N/A"
            return f"{(new_v - old_v) / old_v * 100:+.1f}%"

        print("\n[베이스라인 대비 변화]")
        print(f"  현재 RAG(0.4):   Recall {chg(r_cur, r_base)}, Precision {chg(p_cur, p_base)}, F1 {chg(f_cur, f_base)}")
        print(f"  고도화 RAG:       Recall {chg(r_enh, r_base)}, Precision {chg(p_enh, p_base)}, F1 {chg(f_enh, f_base)}")
        print()
    finally:
        db.close()


if __name__ == "__main__":
    main()
