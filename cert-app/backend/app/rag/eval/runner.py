"""
4-way 평가: baseline / enhanced_reranker / current / current_reranker.
RRF Top30 후보, Reranker는 RRF 상위 20개 pool(RAG_RERANK_POOL_SIZE) → Top4. Retrieval(Recall@5, Recall@10, Precision@5, Precision@10, MRR) + Latency.
"""
import csv
import time
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.rag.eval.golden import load_golden
from app.rag.eval.common import normalize_gold_labels
from app.rag.eval.retrieval_metrics import (
    recall_at_k,
    precision_at_k,
    mrr,
    mrr_at_k,
    recall_at_k_qual,
    mrr_qual,
    ndcg_at_k,
    average_precision,
    success_at_k,
    f1_at_k,
)
from app.rag.retrieve.hybrid import hybrid_retrieve, _fetch_contents_by_chunk_ids, _fetch_qual_names_for_chunk_ids
from app.rag.retrieve.contrastive_retriever import prewarm_contrastive
from app.rag.rerank.cross_encoder import rerank_with_cross_encoder
from app.rag.config import get_rag_settings
from app.rag.index.vector_index import get_vector_search
from app.utils.rag_hybrid import enhanced_rag_03_hybrid
from app.utils.ai import get_embedding
from app.database import SessionLocal
from app.rag.eval.profile_golden import build_user_profile_from_row


def _run_baseline_vector(
    db: Session, query: str, top_k: int, gold_ids: set, query_vec: Optional[Any] = None
) -> tuple:
    """베이스라인: 벡터 유사도만. query_vec 있으면 재사용(질의당 임베딩 1회). 반환 (chunk_ids, latency_ms)."""
    start = time.perf_counter()
    results = get_vector_search(db, query, top_k=top_k, threshold=None, query_vec=query_vec)
    chunk_ids = [r[0] for r in results]
    latency = (time.perf_counter() - start) * 1000
    return chunk_ids, latency


def _run_current_rag(
    db: Session,
    query: str,
    top_k: int,
    gold_ids: set,
    w_d: Optional[float] = None,
    w_s: Optional[float] = None,
    query_vec: Optional[Any] = None,
) -> tuple:
    """현재 프로젝트 RAG: rag_hybrid. w_d, w_s 있으면 RRF 가중치로 사용. 반환 (chunk_ids, latency_ms)."""
    start = time.perf_counter()
    vec = query_vec if query_vec is not None else get_embedding(query)
    qual_ids = enhanced_rag_03_hybrid(db, query, vec, top_k, w_d_override=w_d, w_s_override=w_s)
    chunk_ids = [f"{qid}:0" for qid in qual_ids]
    latency = (time.perf_counter() - start) * 1000
    return chunk_ids, latency


def _run_current_reranker_rag(
    db: Session,
    query: str,
    top_k: int,
    gold_ids: set,
    query_vec: Optional[Any] = None,
    use_reranker: bool = True,
) -> tuple:
    """Current 검색 + (옵션) Cross-Encoder 리랭커. use_reranker=False면 Current 순서만. 반환 (chunk_ids, latency_ms)."""
    start = time.perf_counter()
    settings = get_rag_settings()
    w_d = getattr(settings, "RAG_CURRENT_W_D", None) or 1.0
    w_s = getattr(settings, "RAG_CURRENT_W_S", None) or 1.0
    vec = query_vec if query_vec is not None else get_embedding(query)
    qual_ids = enhanced_rag_03_hybrid(
        db,
        query,
        vec,
        min(top_k * 2, 20),
        w_d_override=w_d,
        w_s_override=w_s,
    )
    chunk_ids = [f"{qid}:0" for qid in qual_ids]
    if use_reranker:
        content_map = _fetch_contents_by_chunk_ids(db, chunk_ids)
        pairs = [(cid, content_map.get(cid, "")) for cid in chunk_ids]
        reranked = rerank_with_cross_encoder(query, pairs, top_k=top_k)
        if reranked:
            chunk_ids = [c[0] for c in reranked]
        else:
            chunk_ids = chunk_ids[:top_k]
    else:
        chunk_ids = chunk_ids[:top_k]
    latency = (time.perf_counter() - start) * 1000
    return chunk_ids, latency


def _run_enhanced_reranker_rag(
    db: Session,
    query: str,
    top_k: int,
    gold_ids: set,
    alpha: Optional[float] = None,
    rrf_w_bm25: Optional[float] = None,
    rrf_w_dense1536: Optional[float] = None,
    rrf_w_contrastive768: Optional[float] = None,
    rrf_k_override: Optional[int] = None,
    use_reranker: bool = True,
    top_n_candidates_override: Optional[int] = None,
    dedup_per_cert_override: Optional[bool] = None,
    bm25_top_n_override: Optional[int] = None,
    vector_top_n_override: Optional[int] = None,
    contrastive_top_n_override: Optional[int] = None,
    vector_threshold_override: Optional[float] = None,
    channels_override: Optional[List[str]] = None,
    force_reranker: bool = False,
    user_profile: Optional[Dict[str, Any]] = None,
) -> tuple:
    """Enhanced RAG: RRF 후보 + (옵션) Cross-Encoder → Top4. use_reranker=False면 검색만. force_reranker=True면 게이팅 무시하고 항상 HF API 호출(평가용)."""
    start = time.perf_counter()
    candidates = hybrid_retrieve(
        db, query, top_k=top_k, filters=None, alpha=alpha, use_reranker=use_reranker,
        rrf_w_bm25=rrf_w_bm25, rrf_w_dense1536=rrf_w_dense1536, rrf_w_contrastive768=rrf_w_contrastive768,
        rrf_k_override=rrf_k_override,
        top_n_candidates_override=top_n_candidates_override,
        dedup_per_cert_override=dedup_per_cert_override,
        bm25_top_n_override=bm25_top_n_override,
        vector_top_n_override=vector_top_n_override,
        contrastive_top_n_override=contrastive_top_n_override,
        vector_threshold_override=vector_threshold_override,
        channels_override=channels_override,
        force_reranker=force_reranker,
        user_profile=user_profile,
    )
    chunk_ids = [c[0] for c in candidates]
    latency = (time.perf_counter() - start) * 1000
    return chunk_ids, latency


def run_eval_three_way(
    golden_path: str,
    output_csv: Optional[str] = None,
    rerank_scores_path: Optional[str] = None,
    verbose: bool = False,
    current_w_d: Optional[float] = None,
    current_w_s: Optional[float] = None,
    enhanced_alpha: Optional[float] = None,
    quiet: bool = False,
    max_queries: Optional[int] = None,
    pipelines: Optional[List[str]] = None,
    rrf_w_bm25: Optional[float] = None,
    rrf_w_dense1536: Optional[float] = None,
    rrf_w_contrastive768: Optional[float] = None,
    rrf_k_override: Optional[int] = None,
    use_reranker: bool = True,
    top_n_candidates_override: Optional[int] = None,
    dedup_per_cert_override: Optional[bool] = None,
    bm25_top_n_override: Optional[int] = None,
    vector_top_n_override: Optional[int] = None,
    contrastive_top_n_override: Optional[int] = None,
    vector_threshold_override: Optional[float] = None,
    force_reranker: bool = True,
) -> Dict[str, Dict[str, float]]:
    """
    골든셋으로 4-way 실행 후 메트릭 집계. RRF 후보는 설정(RAG_TOP_N_CANDIDATES 등)을 따름.
    반환 리스트 길이는 RAG_EVAL_TOP_K(기본 10)로 Recall@5/10·MRR_qual 지표와 정합을 맞춘다.
    force_reranker=True(기본): 평가 시 게이팅 무시하고 항상 HF 리랭커 API 호출해 ON/OFF 차이 반영.
    current_w_d, current_w_s / enhanced_alpha 가 있으면 해당 가중치로 실행.
    verbose=True 이면 질의별 검색 결과 출력.
    반환: { "baseline": {...}, "enhanced_reranker": {...}, "current": {...}, "current_reranker": {...} }
    """
    golden = load_golden(golden_path)
    if not golden:
        return {}

    # max_queries가 지정되면 앞에서 N개만 사용 (빠른 부분 평가용)
    if max_queries is not None and max_queries > 0:
        golden = golden[:max_queries]

    # 평가할 파이프라인 선택 (None이면 전체 4개)
    if pipelines is None:
        pipelines = ["baseline", "current", "current_reranker", "enhanced_reranker"]

    db = SessionLocal()
    golden = normalize_gold_labels(golden, db, drop_empty_gold=True)

    # 3-way(contrastive) 평가 시 첫 질의에서 cold-start가 지연에 포함되지 않도록 한 번만 prewarm
    settings = get_rag_settings()
    # contrastive_only 단독 평가 시에도 첫 질의 cold-start 완화
    if getattr(settings, "RAG_CONTRASTIVE_ENABLE", False) and (
        "enhanced_reranker" in (pipelines or []) or "contrastive_only" in (pipelines or [])
    ):
        prewarm_contrastive()

    per_query_results: List[Dict[str, Any]] = []
    try:
        # 질의별 임베딩 캐시 (실험/파이프라인 간 재사용)
        embedding_cache: Dict[str, Any] = {}

        agg: Dict[str, Dict[str, List[float]]] = {
            pipe: {
                "recall5": [],
                "recall10": [],
                "precision5": [],
                "precision10": [],
                "mrr": [],
                "mrr5": [],
                "mrr10": [],
                "ndcg5": [],
                "ndcg10": [],
                "map": [],
                "f15": [],
                "f110": [],
                "hit5": [],
                "hit10": [],
                "latency": [],
            }
            for pipe in pipelines
        }
        top_k = int(getattr(settings, "RAG_EVAL_TOP_K", 10) or 10)
        # qual_id 단위 정답 집합 (정합화 평가용)
        agg_qual = {pipe: {"recall5_qual": [], "recall10_qual": [], "mrr_qual": []} for pipe in pipelines}
        for row in golden:
            q = row.get("question", "")
            gold_ids = set(row.get("gold_chunk_ids") or [])
            gold_qual_ids = set()
            for cid in gold_ids:
                if cid and ":" in cid:
                    try:
                        gold_qual_ids.add(int(cid.split(":")[0]))
                    except ValueError:
                        pass
            qid = str(row.get("id", q[:32]))

            # 프로필(major/grade/favorite/acquired)이 있으면 hybrid_retrieve에 반영해 dense query rewrite/metadata soft scoring을 강화
            user_profile = build_user_profile_from_row(row, db)

            # 질의당 임베딩 1회: baseline/current 공용 캐시 선충전
            if "baseline" in pipelines or "current" in pipelines:
                embedding_cache.setdefault(q, get_embedding(q))

            # Baseline (벡터만)
            if "baseline" in pipelines:
                ids_b, lat_b = _run_baseline_vector(db, q, top_k, gold_ids, query_vec=embedding_cache.get(q))
                agg["baseline"]["recall5"].append(recall_at_k(ids_b, gold_ids, 5))
                agg["baseline"]["recall10"].append(recall_at_k(ids_b, gold_ids, 10))
                agg["baseline"]["precision5"].append(precision_at_k(ids_b, gold_ids, 5))
                agg["baseline"]["precision10"].append(precision_at_k(ids_b, gold_ids, 10))
                agg["baseline"]["mrr"].append(mrr(ids_b, gold_ids))
                agg["baseline"]["ndcg5"].append(ndcg_at_k(ids_b, gold_ids, 5))
                agg["baseline"]["ndcg10"].append(ndcg_at_k(ids_b, gold_ids, 10))
                agg["baseline"]["map"].append(average_precision(ids_b, gold_ids))
                agg["baseline"]["mrr5"].append(mrr_at_k(ids_b, gold_ids, 5))
                agg["baseline"]["mrr10"].append(mrr_at_k(ids_b, gold_ids, 10))
                agg["baseline"]["f15"].append(f1_at_k(ids_b, gold_ids, 5))
                agg["baseline"]["f110"].append(f1_at_k(ids_b, gold_ids, 10))
                agg["baseline"]["hit5"].append(success_at_k(ids_b, gold_ids, 5))
                agg["baseline"]["hit10"].append(success_at_k(ids_b, gold_ids, 10))
                agg["baseline"]["latency"].append(lat_b)
            else:
                ids_b = []

            # Current (캐시는 위에서 선충전됨)
            if "current" in pipelines:
                vec = embedding_cache[q]
                ids_c, lat_c = _run_current_rag(
                    db,
                    q,
                    top_k,
                    gold_ids,
                    w_d=current_w_d,
                    w_s=current_w_s,
                    query_vec=vec,
                )
                agg["current"]["recall5"].append(recall_at_k(ids_c, gold_ids, 5))
                agg["current"]["recall10"].append(recall_at_k(ids_c, gold_ids, 10))
                agg["current"]["precision5"].append(precision_at_k(ids_c, gold_ids, 5))
                agg["current"]["precision10"].append(precision_at_k(ids_c, gold_ids, 10))
                agg["current"]["mrr"].append(mrr(ids_c, gold_ids))
                agg["current"]["ndcg5"].append(ndcg_at_k(ids_c, gold_ids, 5))
                agg["current"]["ndcg10"].append(ndcg_at_k(ids_c, gold_ids, 10))
                agg["current"]["map"].append(average_precision(ids_c, gold_ids))
                agg["current"]["mrr5"].append(mrr_at_k(ids_c, gold_ids, 5))
                agg["current"]["mrr10"].append(mrr_at_k(ids_c, gold_ids, 10))
                agg["current"]["f15"].append(f1_at_k(ids_c, gold_ids, 5))
                agg["current"]["f110"].append(f1_at_k(ids_c, gold_ids, 10))
                agg["current"]["hit5"].append(success_at_k(ids_c, gold_ids, 5))
                agg["current"]["hit10"].append(success_at_k(ids_c, gold_ids, 10))
                agg["current"]["latency"].append(lat_c)
            else:
                ids_c = []

            # Enhanced Reranker (RRF 후보 + (옵션) Cross-Encoder → Top4; 3-way 시 가중치 오버라이드)
            if "enhanced_reranker" in pipelines:
                ids_er, lat_er = _run_enhanced_reranker_rag(
                    db, q, top_k, gold_ids, alpha=enhanced_alpha,
                    rrf_w_bm25=rrf_w_bm25, rrf_w_dense1536=rrf_w_dense1536, rrf_w_contrastive768=rrf_w_contrastive768,
                    rrf_k_override=rrf_k_override,
                    use_reranker=use_reranker,
                    top_n_candidates_override=top_n_candidates_override,
                    dedup_per_cert_override=dedup_per_cert_override,
                    bm25_top_n_override=bm25_top_n_override,
                    vector_top_n_override=vector_top_n_override,
                    contrastive_top_n_override=contrastive_top_n_override,
                    vector_threshold_override=vector_threshold_override,
                    force_reranker=force_reranker,
                    user_profile=user_profile,
                )
                agg["enhanced_reranker"]["recall5"].append(recall_at_k(ids_er, gold_ids, 5))
                agg["enhanced_reranker"]["recall10"].append(recall_at_k(ids_er, gold_ids, 10))
                agg["enhanced_reranker"]["precision5"].append(precision_at_k(ids_er, gold_ids, 5))
                agg["enhanced_reranker"]["precision10"].append(precision_at_k(ids_er, gold_ids, 10))
                agg["enhanced_reranker"]["mrr"].append(mrr(ids_er, gold_ids))
                agg["enhanced_reranker"]["ndcg5"].append(ndcg_at_k(ids_er, gold_ids, 5))
                agg["enhanced_reranker"]["ndcg10"].append(ndcg_at_k(ids_er, gold_ids, 10))
                agg["enhanced_reranker"]["map"].append(average_precision(ids_er, gold_ids))
                agg["enhanced_reranker"]["mrr5"].append(mrr_at_k(ids_er, gold_ids, 5))
                agg["enhanced_reranker"]["mrr10"].append(mrr_at_k(ids_er, gold_ids, 10))
                agg["enhanced_reranker"]["f15"].append(f1_at_k(ids_er, gold_ids, 5))
                agg["enhanced_reranker"]["f110"].append(f1_at_k(ids_er, gold_ids, 10))
                agg["enhanced_reranker"]["hit5"].append(success_at_k(ids_er, gold_ids, 5))
                agg["enhanced_reranker"]["hit10"].append(success_at_k(ids_er, gold_ids, 10))
                agg["enhanced_reranker"]["latency"].append(lat_er)
                agg_qual["enhanced_reranker"]["recall5_qual"].append(recall_at_k_qual(ids_er, gold_qual_ids, 5))
                agg_qual["enhanced_reranker"]["recall10_qual"].append(recall_at_k_qual(ids_er, gold_qual_ids, 10))
                agg_qual["enhanced_reranker"]["mrr_qual"].append(mrr_qual(ids_er, gold_qual_ids))
            else:
                ids_er = []

            # Enhanced Reranker 동일 경로이나 contrastive 채널 제외 (BM25 + dense1536만 RRF → 리랭커)
            if "enhanced_reranker_no_contrastive" in pipelines:
                ids_er_nc, lat_er_nc = _run_enhanced_reranker_rag(
                    db, q, top_k, gold_ids, alpha=enhanced_alpha,
                    rrf_w_bm25=rrf_w_bm25, rrf_w_dense1536=rrf_w_dense1536, rrf_w_contrastive768=rrf_w_contrastive768,
                    rrf_k_override=rrf_k_override,
                    use_reranker=use_reranker,
                    top_n_candidates_override=top_n_candidates_override,
                    dedup_per_cert_override=dedup_per_cert_override,
                    bm25_top_n_override=bm25_top_n_override,
                    vector_top_n_override=vector_top_n_override,
                    contrastive_top_n_override=contrastive_top_n_override,
                    vector_threshold_override=vector_threshold_override,
                    channels_override=["bm25", "vector"],
                    force_reranker=force_reranker,
                    user_profile=user_profile,
                )
                agg["enhanced_reranker_no_contrastive"]["recall5"].append(recall_at_k(ids_er_nc, gold_ids, 5))
                agg["enhanced_reranker_no_contrastive"]["recall10"].append(recall_at_k(ids_er_nc, gold_ids, 10))
                agg["enhanced_reranker_no_contrastive"]["precision5"].append(precision_at_k(ids_er_nc, gold_ids, 5))
                agg["enhanced_reranker_no_contrastive"]["precision10"].append(precision_at_k(ids_er_nc, gold_ids, 10))
                agg["enhanced_reranker_no_contrastive"]["mrr"].append(mrr(ids_er_nc, gold_ids))
                agg["enhanced_reranker_no_contrastive"]["ndcg5"].append(ndcg_at_k(ids_er_nc, gold_ids, 5))
                agg["enhanced_reranker_no_contrastive"]["ndcg10"].append(ndcg_at_k(ids_er_nc, gold_ids, 10))
                agg["enhanced_reranker_no_contrastive"]["map"].append(average_precision(ids_er_nc, gold_ids))
                agg["enhanced_reranker_no_contrastive"]["mrr5"].append(mrr_at_k(ids_er_nc, gold_ids, 5))
                agg["enhanced_reranker_no_contrastive"]["mrr10"].append(mrr_at_k(ids_er_nc, gold_ids, 10))
                agg["enhanced_reranker_no_contrastive"]["f15"].append(f1_at_k(ids_er_nc, gold_ids, 5))
                agg["enhanced_reranker_no_contrastive"]["f110"].append(f1_at_k(ids_er_nc, gold_ids, 10))
                agg["enhanced_reranker_no_contrastive"]["hit5"].append(success_at_k(ids_er_nc, gold_ids, 5))
                agg["enhanced_reranker_no_contrastive"]["hit10"].append(success_at_k(ids_er_nc, gold_ids, 10))
                agg["enhanced_reranker_no_contrastive"]["latency"].append(lat_er_nc)
                agg_qual["enhanced_reranker_no_contrastive"]["recall5_qual"].append(recall_at_k_qual(ids_er_nc, gold_qual_ids, 5))
                agg_qual["enhanced_reranker_no_contrastive"]["recall10_qual"].append(recall_at_k_qual(ids_er_nc, gold_qual_ids, 10))
                agg_qual["enhanced_reranker_no_contrastive"]["mrr_qual"].append(mrr_qual(ids_er_nc, gold_qual_ids))

            # 단일 채널 기여도 (BM25 only / Vector only / Contrastive only)
            def _run_channel(channels: List[str]) -> tuple:
                return _run_enhanced_reranker_rag(
                    db, q, top_k, gold_ids, alpha=enhanced_alpha,
                    rrf_w_bm25=rrf_w_bm25, rrf_w_dense1536=rrf_w_dense1536, rrf_w_contrastive768=rrf_w_contrastive768,
                    rrf_k_override=rrf_k_override,
                    use_reranker=use_reranker,
                    top_n_candidates_override=top_n_candidates_override,
                    dedup_per_cert_override=dedup_per_cert_override,
                    bm25_top_n_override=bm25_top_n_override,
                    vector_top_n_override=vector_top_n_override,
                    contrastive_top_n_override=contrastive_top_n_override,
                    vector_threshold_override=vector_threshold_override,
                    channels_override=channels,
                    force_reranker=force_reranker,
                    user_profile=user_profile,
                )
            for ch_name, ch_list in [("bm25_only", ["bm25"]), ("vector_only", ["vector"]), ("contrastive_only", ["contrastive"])]:
                if ch_name in pipelines:
                    ids_ch, lat_ch = _run_channel(ch_list)
                    agg[ch_name]["recall5"].append(recall_at_k(ids_ch, gold_ids, 5))
                    agg[ch_name]["recall10"].append(recall_at_k(ids_ch, gold_ids, 10))
                    agg[ch_name]["precision5"].append(precision_at_k(ids_ch, gold_ids, 5))
                    agg[ch_name]["precision10"].append(precision_at_k(ids_ch, gold_ids, 10))
                    agg[ch_name]["mrr"].append(mrr(ids_ch, gold_ids))
                    agg[ch_name]["ndcg5"].append(ndcg_at_k(ids_ch, gold_ids, 5))
                    agg[ch_name]["ndcg10"].append(ndcg_at_k(ids_ch, gold_ids, 10))
                    agg[ch_name]["map"].append(average_precision(ids_ch, gold_ids))
                    agg[ch_name]["mrr5"].append(mrr_at_k(ids_ch, gold_ids, 5))
                    agg[ch_name]["mrr10"].append(mrr_at_k(ids_ch, gold_ids, 10))
                    agg[ch_name]["f15"].append(f1_at_k(ids_ch, gold_ids, 5))
                    agg[ch_name]["f110"].append(f1_at_k(ids_ch, gold_ids, 10))
                    agg[ch_name]["hit5"].append(success_at_k(ids_ch, gold_ids, 5))
                    agg[ch_name]["hit10"].append(success_at_k(ids_ch, gold_ids, 10))
                    agg[ch_name]["latency"].append(lat_ch)
                    if ch_name in agg_qual:
                        agg_qual[ch_name]["recall5_qual"].append(recall_at_k_qual(ids_ch, gold_qual_ids, 5))
                        agg_qual[ch_name]["recall10_qual"].append(recall_at_k_qual(ids_ch, gold_qual_ids, 10))
                        agg_qual[ch_name]["mrr_qual"].append(mrr_qual(ids_ch, gold_qual_ids))

            # Current + 리랭커 (Current RRF 후보, pool → Reranker Top4)
            if "current_reranker" in pipelines:
                embedding_cache.setdefault(q, get_embedding(q))
                vec = embedding_cache[q]
                ids_cr, lat_cr = _run_current_reranker_rag(
                    db,
                    q,
                    top_k,
                    gold_ids,
                    query_vec=vec,
                    use_reranker=use_reranker,
                )
                agg["current_reranker"]["recall5"].append(recall_at_k(ids_cr, gold_ids, 5))
                agg["current_reranker"]["recall10"].append(recall_at_k(ids_cr, gold_ids, 10))
                agg["current_reranker"]["precision5"].append(precision_at_k(ids_cr, gold_ids, 5))
                agg["current_reranker"]["precision10"].append(precision_at_k(ids_cr, gold_ids, 10))
                agg["current_reranker"]["mrr"].append(mrr(ids_cr, gold_ids))
                agg["current_reranker"]["ndcg5"].append(ndcg_at_k(ids_cr, gold_ids, 5))
                agg["current_reranker"]["ndcg10"].append(ndcg_at_k(ids_cr, gold_ids, 10))
                agg["current_reranker"]["map"].append(average_precision(ids_cr, gold_ids))
                agg["current_reranker"]["mrr5"].append(mrr_at_k(ids_cr, gold_ids, 5))
                agg["current_reranker"]["mrr10"].append(mrr_at_k(ids_cr, gold_ids, 10))
                agg["current_reranker"]["f15"].append(f1_at_k(ids_cr, gold_ids, 5))
                agg["current_reranker"]["f110"].append(f1_at_k(ids_cr, gold_ids, 10))
                agg["current_reranker"]["hit5"].append(success_at_k(ids_cr, gold_ids, 5))
                agg["current_reranker"]["hit10"].append(success_at_k(ids_cr, gold_ids, 10))
                agg["current_reranker"]["latency"].append(lat_cr)
            else:
                ids_cr = []

            if verbose:
                per_query_results.append({
                    "id": qid,
                    "question": q,
                    "gold_chunk_ids": list(gold_ids),
                    "baseline_top4": ids_b,
                    "enhanced_reranker_top4": ids_er,
                    "current_top4": ids_c,
                    "current_reranker_top4": ids_cr,
                })

        if verbose and per_query_results:
            all_cids: List[str] = []
            for r in per_query_results:
                for key in (
                    "baseline_top4",
                    "enhanced_reranker_top4",
                    "current_top4",
                    "current_reranker_top4",
                ):
                    for cid in r.get(key) or []:
                        if cid:
                            all_cids.append(cid)
            name_by_chunk = _fetch_qual_names_for_chunk_ids(db, list(dict.fromkeys(all_cids)))

            def _cert_labels(chunk_ids: List[str]) -> List[str]:
                out: List[str] = []
                for cid in chunk_ids or []:
                    nm = (name_by_chunk.get(cid) or "").strip()
                    out.append(nm if nm else str(cid))
                return out

            print("\n[ 질의별 검색 결과 (Top4) ]")
            print("=" * 70)
            for r in per_query_results:
                print(f"\n  [id] {r['id']}")
                print(f"  [question] {r['question']}")
                print(f"  [gold_chunk_ids] {r['gold_chunk_ids']}")
                print(f"  [baseline_top4] {r['baseline_top4']}")
                print(f"  [baseline_top4_자격증명] {_cert_labels(r['baseline_top4'])}")
                print(f"  [enhanced_reranker_top4] {r['enhanced_reranker_top4']}")
                print(f"  [enhanced_reranker_top4_자격증명] {_cert_labels(r['enhanced_reranker_top4'])}")
                print(f"  [current_top4] {r['current_top4']}")
                print(f"  [current_top4_자격증명] {_cert_labels(r['current_top4'])}")
                print(f"  [current_reranker_top4] {r['current_reranker_top4']}")
                print(f"  [current_reranker_top4_자격증명] {_cert_labels(r['current_reranker_top4'])}")
            print("=" * 70)

        def avg(x: List[float]) -> float:
            return sum(x) / len(x) if x else 0.0

        def p95(x: List[float]) -> float:
            if not x:
                return 0.0
            s = sorted(x)
            i = int(len(s) * 0.95) - 1
            return s[min(max(i, 0), len(s) - 1)]

        results: Dict[str, Dict[str, float]] = {}
        for name, vals in agg.items():
            results[name] = {
                "Recall@5": avg(vals["recall5"]),
                "Recall@10": avg(vals["recall10"]),
                "Precision@5": avg(vals["precision5"]),
                "Precision@10": avg(vals["precision10"]),
                "MRR": avg(vals["mrr"]),
                "MRR@5": avg(vals["mrr5"]),
                "MRR@10": avg(vals["mrr10"]),
                "NDCG@5": avg(vals["ndcg5"]),
                "NDCG@10": avg(vals["ndcg10"]),
                "MAP": avg(vals["map"]),
                "F1@5": avg(vals["f15"]),
                "F1@10": avg(vals["f110"]),
                "Hit@5": avg(vals["hit5"]),
                "Hit@10": avg(vals["hit10"]),
                "Avg_Latency_ms": avg(vals["latency"]),
                "P95_Latency_ms": p95(vals["latency"]),
            }
            if agg_qual.get(name):
                qv = agg_qual[name]
                results[name]["Recall@5_qual"] = avg(qv["recall5_qual"])
                results[name]["Recall@10_qual"] = avg(qv["recall10_qual"])
                results[name]["MRR_qual"] = avg(qv["mrr_qual"])

        if output_csv:
            csv_cols = [
                "pipeline", "Recall@5", "Recall@10", "Precision@5", "Precision@10", "MRR", "MRR@5", "MRR@10",
                "NDCG@5", "NDCG@10", "MAP", "F1@5", "F1@10", "Hit@5", "Hit@10",
                "Avg_Latency_ms", "P95_Latency_ms",
            ]
            with open(output_csv, "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow(csv_cols)
                for name, row in results.items():
                    w.writerow([name] + [row.get(k, 0) for k in csv_cols[1:]])

        # 콘솔 표 (quiet 시 스킵)
        if not quiet:
            print("\n[ RAG 4-way Eval ]")
            print("-" * 60)
            for name, row in results.items():
                line = (
                    f"  {name}: R@5={row['Recall@5']:.3f} R@10={row['Recall@10']:.3f} "
                    f"P@5={row['Precision@5']:.3f} P@10={row['Precision@10']:.3f} MRR={row['MRR']:.3f} MRR@5={row.get('MRR@5', 0):.3f} MRR@10={row.get('MRR@10', 0):.3f} "
                    f"NDCG@5={row.get('NDCG@5', 0):.3f} NDCG@10={row.get('NDCG@10', 0):.3f} MAP={row.get('MAP', 0):.3f} "
                    f"F1@5={row.get('F1@5', 0):.3f} F1@10={row.get('F1@10', 0):.3f} H@5={row.get('Hit@5', 0):.3f} H@10={row.get('Hit@10', 0):.3f} "
                    f"avg_ms={row['Avg_Latency_ms']:.0f} p95_ms={row['P95_Latency_ms']:.0f}"
                )
                if name == "enhanced_reranker" and "Recall@5_qual" in row:
                    line += f"  [qual] R@5={row['Recall@5_qual']:.3f} R@10={row['Recall@10_qual']:.3f} MRR={row['MRR_qual']:.3f}"
                print(line)
            print("-" * 60)
        return results
    finally:
        db.close()
