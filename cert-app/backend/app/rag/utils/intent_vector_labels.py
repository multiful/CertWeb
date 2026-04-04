import logging
from typing import Dict, FrozenSet, Iterable, List, Optional

from sqlalchemy import text

from app.config import get_settings
from app.database import SessionLocal

logger = logging.getLogger(__name__)
settings = get_settings()

# DB 허용 도메인/상위도메인 캐시 (재질의에서만 사용, intent_labels distinct label)
_allowed_domains_cache: FrozenSet[str] | None = None
_allowed_top_domains_cache: FrozenSet[str] | None = None


def _is_enabled() -> bool:
    """Supabase/Postgres intent 라벨 벡터 테이블 사용 여부."""
    return bool(getattr(settings, "INTENT_LABEL_LOOKUP_ENABLE", False))


def lookup_intent_labels_with_vector(
    query: str,
    kinds: Iterable[str],
    top_k: int = 1,
    min_similarity: float | None = None,
    query_embedding: Optional[List[float]] = None,
) -> Dict[str, str]:
    """
    룰 기반 슬롯 추출이 애매한 경우 Supabase 벡터 intent 라벨 테이블에서 보정용 라벨을 조회한다.

    - query: 원문 (임베딩이 없을 때만 get_embedding 입력으로 사용)
    - kinds: ["job", "purpose", "major", "domain"] 등 조회할 intent 종류
    - top_k: kind **별** 최근접 라벨 개수 (기본 1)
    - query_embedding: 호출자가 이미 구한 쿼리 임베딩이면 전달해 OpenAI 중복 호출 방지
    """
    if not _is_enabled():
        return {}

    q = (query or "").strip()
    if not q and not query_embedding:
        return {}

    embedding: List[float] | None = query_embedding
    if embedding is None or not isinstance(embedding, list) or not embedding:
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
        # kind별로 가장 가까운 라벨만 선택 (전역 ORDER BY + LIMIT는
        # 한 kind(예: job)만 여러 행 돌려 purpose/major를 비우는 버그가 있었음)
        sql = text(
            """
            SELECT kind, label
            FROM (
                SELECT kind,
                       label,
                       ROW_NUMBER() OVER (
                           PARTITION BY kind
                           ORDER BY embedding <=> :embedding
                       ) AS rn
                FROM intent_labels
                WHERE kind = ANY(:kinds)
                  AND embedding IS NOT NULL
                  AND (embedding <=> :embedding) <= :max_distance
            ) t
            WHERE t.rn <= :top_per_kind
            ORDER BY kind
            """
        )
        rows = db.execute(
            sql,
            {
                "embedding": str(embedding),
                "kinds": kinds_list,
                "max_distance": max_distance,
                "top_per_kind": max(1, top_k),
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


def get_allowed_domains_from_db() -> FrozenSet[str]:
    """
    intent_labels 테이블에서 kind='domain'인 label 목록.
    재질의 시 도메인은 이 집합에 있는 값만 사용 (DB 기준).
    """
    global _allowed_domains_cache
    if _allowed_domains_cache is not None:
        return _allowed_domains_cache
    db = SessionLocal()
    try:
        rows = db.execute(
            text("SELECT DISTINCT label FROM intent_labels WHERE kind = 'domain' AND label IS NOT NULL AND label != ''")
        ).fetchall()
        labels = frozenset(str(getattr(r, "label", "")).strip() for r in rows if getattr(r, "label", None))
        _allowed_domains_cache = labels
        return _allowed_domains_cache
    except Exception:
        logger.debug("get_allowed_domains_from_db failed", exc_info=True)
        _allowed_domains_cache = frozenset()
        return _allowed_domains_cache
    finally:
        db.close()


def get_allowed_top_domains_from_db() -> FrozenSet[str]:
    """
    intent_labels 테이블에서 kind='top_domain'인 label 목록.
    재질의 시 정규화도메인(상위)은 이 집합에 있는 값만 사용 (DB 기준).
    top_domain이 DB에 없으면 domain_tokens JSON의 top_domains 키로 폴백.
    """
    global _allowed_top_domains_cache
    if _allowed_top_domains_cache is not None:
        return _allowed_top_domains_cache
    db = SessionLocal()
    try:
        rows = db.execute(
            text(
                "SELECT DISTINCT label FROM intent_labels WHERE kind = 'top_domain' AND label IS NOT NULL AND label != ''"
            )
        ).fetchall()
        labels = frozenset(str(getattr(r, "label", "")).strip() for r in rows if getattr(r, "label", None))
        if labels:
            _allowed_top_domains_cache = labels
            return _allowed_top_domains_cache
    except Exception:
        logger.debug("get_allowed_top_domains_from_db failed", exc_info=True)
    finally:
        db.close()
    # DB에 top_domain이 없으면 dataset/domain.txt 기준 상위 도메인 사용 (DB 업로드 불필요)
    try:
        from app.rag.utils.domain_txt_loader import get_top_domains_from_domain_txt
        labels = get_top_domains_from_domain_txt()
        if labels:
            _allowed_top_domains_cache = labels
            return _allowed_top_domains_cache
    except Exception:
        pass
    try:
        from app.rag.utils.domain_tokens import _broad_domains_path
        import json
        path = _broad_domains_path()
        if path.is_file():
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            top_domains = data.get("top_domains") or {}
            labels = frozenset(str(k).strip() for k in top_domains if k)
            _allowed_top_domains_cache = labels
            return _allowed_top_domains_cache
    except Exception:
        pass
    _allowed_top_domains_cache = frozenset()
    return _allowed_top_domains_cache

