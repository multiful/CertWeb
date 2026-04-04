"""
dense_slot_labels 테이블 기반 슬롯 벡터 라벨 조회.

- 쿼리 임베딩과 slot_type별 라벨 임베딩의 코사인 유사도로
  domain / difficulty / job / purpose / major 중 하나에 대한 최적 라벨(label_text) 반환.
- RAG_DENSE_SLOT_VECTOR_FALLBACK_ENABLE=True 일 때 dense_query_rewrite에서 보정용으로 사용.
"""

import logging
from typing import List, Optional

from sqlalchemy import text

from app.database import SessionLocal

logger = logging.getLogger(__name__)


def _is_enabled() -> bool:
    from app.rag.config import get_rag_settings
    return bool(getattr(get_rag_settings(), "RAG_DENSE_SLOT_VECTOR_FALLBACK_ENABLE", False))


def lookup_slot_label_with_vector(
    query: str,
    slot_type: str,
    top_k: int = 1,
    min_similarity: Optional[float] = None,
    query_embedding: Optional[List[float]] = None,
) -> Optional[str]:
    """
    쿼리와 slot_type에 해당하는 dense_slot_labels 중 가장 유사한 라벨의 label_text 반환.

    - query: 원문 질의 (임베딩이 없을 때만 사용)
    - slot_type: 'domain' | 'difficulty' | 'job' | 'purpose' | 'major'
    - query_embedding: 이미 계산된 쿼리 벡터 (재질의 파이프라인에서 OpenAI 중복 호출 방지)
    """
    if not _is_enabled():
        return None

    valid = {"domain", "difficulty", "job", "purpose", "major"}
    if slot_type not in valid:
        return None

    q = (query or "").strip()
    if not q and not query_embedding:
        return None

    embedding: Optional[List[float]] = query_embedding
    if embedding is None or not isinstance(embedding, list) or not embedding:
        try:
            from app.utils.ai import get_embedding
        except Exception:
            logger.debug("slot_vector_labels: get_embedding import failed", exc_info=True)
            return None

        try:
            embedding = get_embedding(q)
        except Exception:
            logger.debug("slot_vector_labels: get_embedding failed", exc_info=True)
            return None

    if not isinstance(embedding, list) or not embedding:
        return None

    from app.rag.config import get_rag_settings
    _rag = get_rag_settings()
    sim_threshold = (
        float(min_similarity)
        if min_similarity is not None
        else float(getattr(_rag, "RAG_DENSE_SLOT_VECTOR_MIN_SIM", 0.5))
    )
    sim_threshold = max(0.0, min(0.99, sim_threshold))
    max_distance = 1.0 - sim_threshold

    db = SessionLocal()
    try:
        sql = text(
            """
            SELECT label_text,
                   (1 - (embedding <=> :embedding)) AS similarity
            FROM dense_slot_labels
            WHERE slot_type = :slot_type
              AND active = true
              AND (embedding <=> :embedding) <= :max_distance
            ORDER BY embedding <=> :embedding
            LIMIT :limit
            """
        )
        rows = db.execute(
            sql,
            {
                "embedding": str(embedding),
                "slot_type": slot_type,
                "max_distance": max_distance,
                "limit": max(1, top_k),
            },
        ).fetchall()
    except Exception as e:
        logger.debug("slot_vector_labels: DB lookup failed: %s", e, exc_info=True)
        return None
    finally:
        db.close()  # 세션 종료 시 ROLLBACK 로그는 정상(미커밋 트랜잭션). 조회 실패 시 위 except에서 None 반환. pgvector가 embedding을 문자열로 비교해 실패하면 예외 발생 가능 → Supabase에서는 CAST(:embedding AS vector) 등 확인.

    if not rows:
        return None
    r = rows[0]
    label_text = getattr(r, "label_text", None)
    return str(label_text).strip() if label_text else None
