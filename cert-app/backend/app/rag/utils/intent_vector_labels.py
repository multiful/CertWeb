import logging
from typing import Dict, Iterable, List

from sqlalchemy import text

from app.config import get_settings
from app.database import SessionLocal

logger = logging.getLogger(__name__)
settings = get_settings()


def _is_enabled() -> bool:
    """Supabase/Postgres intent 라벨 벡터 테이블 사용 여부."""
    return bool(getattr(settings, "INTENT_LABEL_LOOKUP_ENABLE", False))


def lookup_intent_labels_with_vector(
    query: str,
    kinds: Iterable[str],
    top_k: int = 1,
    min_similarity: float | None = None,
) -> Dict[str, str]:
    """
    룰 기반 슬롯 추출이 애매한 경우 Supabase 벡터 intent 라벨 테이블에서 보정용 라벨을 조회한다.

    - query: raw query (원문) 전체를 임베딩하여 intent 라벨과 코사인 유사도 매칭
    - kinds: ["job", "purpose"] 등 조회할 intent 종류 (희망직무, 목적)
    - top_k: 각 kind 당 최대 몇 개까지 후보를 허용할지 (현재는 첫 번째 후보만 사용)
    - min_similarity: 최소 코사인 유사도 (기본값 settings.INTENT_LABEL_MIN_SIMILARITY)
    """
    if not _is_enabled():
        return {}

    q = (query or "").strip()
    if not q:
        return {}

    try:
        from app.utils.ai import get_embedding
    except Exception:
        logger.debug("intent_vector_labels: get_embedding import failed", exc_info=True)
        return {}

    try:
        embedding = get_embedding(q)
    except Exception:
        logger.debug("intent_vector_labels: get_embedding failed", exc_info=True)
        return {}

    if not isinstance(embedding, list) or not embedding:
        return {}

    kinds_list: List[str] = [k for k in kinds if k]
    if not kinds_list:
        return {}

    sim_threshold = (
        float(min_similarity)
        if min_similarity is not None
        else float(getattr(settings, "INTENT_LABEL_MIN_SIMILARITY", 0.75))
    )
    if sim_threshold <= 0:
        sim_threshold = 0.0
    if sim_threshold >= 1:
        sim_threshold = 0.99
    max_distance = 1.0 - sim_threshold

    db = SessionLocal()
    try:
        sql = text(
            """
            SELECT kind,
                   label,
                   (1 - (embedding <=> :embedding)) AS similarity
            FROM intent_labels
            WHERE kind = ANY(:kinds)
              AND (embedding <=> :embedding) <= :max_distance
            ORDER BY embedding <=> :embedding
            LIMIT :limit
            """
        )
        rows = db.execute(
            sql,
            {
                "embedding": str(embedding),
                "kinds": kinds_list,
                "max_distance": max_distance,
                "limit": max(1, top_k) * len(kinds_list),
            },
        ).fetchall()
    except Exception:
        logger.debug("intent_vector_labels: DB lookup failed", exc_info=True)
        return {}
    finally:
        db.close()

    out: Dict[str, str] = {}
    for r in rows:
        kind = getattr(r, "kind", None)
        label = getattr(r, "label", None)
        if not kind or not label:
            continue
        if kind in out:
            continue
        out[kind] = str(label)
    return out

