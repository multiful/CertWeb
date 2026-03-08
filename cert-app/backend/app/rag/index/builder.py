"""
인덱스 구축: DB certificates_vectors에서 청크 로드 → BM25 인덱스 빌드 → 디스크 저장.

Plain BM25: 문서 텍스트는 bm25_text(또는 content)만 사용. name 부스팅/접두사 없음.
doc_id: qual_id:chunk_index 유지.
"""
from pathlib import Path
from typing import Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.rag.config import get_rag_index_dir, get_rag_settings
from app.rag.index.bm25_index import BM25Index


def build_bm25_from_db(
    db: Session,
    index_dir: Optional[Path] = None,
    use_korean_ngram: Optional[bool] = None,
    name_boost: Optional[bool] = None,
) -> Path:
    """
    certificates_vectors에서 (qual_id, chunk_index, content, bm25_text[, name]) 조회 후
    COALESCE(bm25_text, content) 로 BM25 인덱스 빌드.
    use_korean_ngram: None이면 get_rag_settings().RAG_BM25_USE_KOREAN_NGRAM 사용.
    name_boost: None이면 get_rag_settings().RAG_BM25_NAME_BOOST 사용.
    """
    settings = get_rag_settings()
    if use_korean_ngram is None:
        use_korean_ngram = getattr(settings, "RAG_BM25_USE_KOREAN_NGRAM", True)
    if name_boost is None:
        name_boost = getattr(settings, "RAG_BM25_NAME_BOOST", True)
    index_dir = index_dir or get_rag_index_dir()
    path = Path(index_dir) / "bm25.pkl"

    try:
        rows = db.execute(
            text("""
                SELECT v.qual_id, v.chunk_index, v.content, v.bm25_text,
                       COALESCE(v.name, q.qual_name) AS qual_name
                FROM certificates_vectors v
                LEFT JOIN qualification q ON q.qual_id = v.qual_id
                WHERE v.content IS NOT NULL AND TRIM(v.content) != ''
            """)
        ).fetchall()
    except Exception:
        try:
            rows = db.execute(
                text("""
                    SELECT qual_id, chunk_index, content, bm25_text
                    FROM certificates_vectors
                    WHERE content IS NOT NULL AND TRIM(content) != ''
                """)
            ).fetchall()
        except Exception:
            rows = []

    documents = []
    for r in rows:
        chunk_id = f"{r.qual_id}:{getattr(r, 'chunk_index', 0)}"
        content = (getattr(r, "content", None) or "").replace("\n", " ").strip()
        bm25_text = (getattr(r, "bm25_text", None) or "").strip()
        doc_text = bm25_text if bm25_text else content
        if not doc_text:
            doc_text = " "
        if name_boost:
            qual_name = (getattr(r, "qual_name", None) or "").strip()
            if qual_name:
                doc_text = f"{qual_name} {qual_name} {doc_text}"
        documents.append({
            "chunk_id": chunk_id,
            "text": doc_text,
        })

    settings = get_rag_settings()
    k1 = getattr(settings, "RAG_BM25_K1", None)
    b = getattr(settings, "RAG_BM25_B", None)
    k1 = float(k1) if k1 is not None else 1.5
    b = float(b) if b is not None else 0.75
    bm25 = BM25Index(index_path=path)
    bm25.build(documents, use_korean_ngram=use_korean_ngram, k1=k1, b=b)
    bm25.save(path)
    return path
