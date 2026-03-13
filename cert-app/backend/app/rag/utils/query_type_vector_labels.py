import logging
from typing import Optional

from sqlalchemy import text

from app.database import SessionLocal
from app.utils.ai import get_embedding

logger = logging.getLogger(__name__)


def lookup_query_type_with_vector(
    query: str,
    major: Optional[str] = None,
    grade_level: Optional[int] = None,
    min_similarity: float = 0.75,
) -> Optional[str]:
    """
    raw_query(+선택적 프로필 정보)를 임베딩해 Supabase Postgres의 query_type_labels 테이블에서
    가장 유사한 query_type 하나를 조회한다.

    - query: 원문 질의 (필수)
    - major, grade_level: 프로필 정보가 있을 경우 함께 넣어 intent를 더 안정적으로 매칭
    - min_similarity: 최소 코사인 유사도 (기본 0.75). 이보다 낮으면 None 반환.
    """
    q = (query or "").strip()
    if not q:
        return None

    # 임베딩용 텍스트: raw_query + 프로필 정보를 한 번에 넣어 시맨틱 매칭 강화
    parts = [q]
    if major:
        parts.append(f"전공: {major}")
    if grade_level is not None:
        try:
            g = int(grade_level)
            if 1 <= g <= 4:
                parts.append(f"{g}학년")
        except (TypeError, ValueError):
            pass
    text_for_embedding = "\n".join(parts).strip()
    if not text_for_embedding:
        text_for_embedding = q

    try:
        embedding = get_embedding(text_for_embedding)
    except Exception:
        logger.debug("query_type_vector_labels: get_embedding failed", exc_info=True)
        return None

    if not isinstance(embedding, list) or not embedding:
        return None

    # 코사인 유사도 threshold -> pgvector 거리 threshold
    sim = float(min_similarity)
    if sim <= 0:
        sim = 0.0
    if sim >= 1:
        sim = 0.99
    max_distance = 1.0 - sim

    db = SessionLocal()
    try:
        sql = text(
            """
            SELECT query_type,
                   raw_query,
                   (1 - (embedding <=> :embedding)) AS similarity
            FROM query_type_labels
            WHERE (embedding <=> :embedding) <= :max_distance
            ORDER BY embedding <=> :embedding
            LIMIT 1
            """
        )
        row = db.execute(
            sql,
            {
                "embedding": str(embedding),
                "max_distance": max_distance,
            },
        ).fetchone()
    except Exception:
        logger.debug("query_type_vector_labels: DB lookup failed", exc_info=True)
        return None
    finally:
        db.close()

    if not row or not getattr(row, "query_type", None):
        return None
    return str(row.query_type)

