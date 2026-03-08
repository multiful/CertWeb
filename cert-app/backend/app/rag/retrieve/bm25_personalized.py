"""
BM25 전용 검색: current_bm25_single (expand_query_single_string + 1회 검색).
개인화 모드 제거 — 단일 경로만 유지. hybrid_retrieve 등에서 동일 인덱스 사용.
"""
import logging
from pathlib import Path
from typing import List, Optional, Tuple

from sqlalchemy.orm import Session

from app.rag.config import get_rag_index_dir
from app.rag.eval.query_type import classify_query_type
from app.rag.index.bm25_index import BM25Index
from app.rag.utils.query_processor import expand_query_single_string

logger = logging.getLogger(__name__)


def bm25_retrieve_personalized(
    db: Session,
    query: str,
    top_k: int,
    profile: Optional[object] = None,
    personalization_mode: Optional[str] = None,
    *,
    acquired_exclude: bool = False,
) -> List[Tuple[str, float]]:
    """
    BM25 단일 경로 검색 (current_bm25_single).
    profile, personalization_mode, acquired_exclude는 무시 — 호환성만 유지.

    - 쿼리: expand_query_single_string(query, for_recommendation=True)
    - 검색: 1회, 상위 top_k개 반환.

    반환: [(chunk_id, score), ...]
    """
    index_path = get_rag_index_dir() / "bm25.pkl"
    if not index_path.exists():
        logger.warning("BM25 index file not found: %s", index_path)
        return []

    try:
        bm25 = BM25Index(index_path=index_path)
        bm25.load()
    except Exception as e:
        logger.warning("BM25 load failed: %s", e)
        return []

    query_type = classify_query_type(query, from_golden=None)
    bm25_query = expand_query_single_string(query, for_recommendation=True, query_type=query_type)
    raw = bm25.search(bm25_query, k=top_k)
    return raw[:top_k]
