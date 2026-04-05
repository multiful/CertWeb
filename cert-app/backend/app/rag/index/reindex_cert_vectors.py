"""
DB 코퍼스(qualification) -> certificates_vectors 증분 재색인.

포인트:
- canonical text + chunk profile 적용
- batch 임베딩/upsert (변경분만 임베딩)
"""
from __future__ import annotations

import argparse
import hashlib
import logging
import time
from dataclasses import dataclass
from typing import Dict, List, Optional

from sqlalchemy import text

from app.database import SessionLocal
from app.rag.config import get_rag_settings
from app.rag.ingest.chunker import (
    build_canonical_metadata_from_row,
    section_chunk_with_metadata,
)
from app.rag.ingest.canonical_text import build_bm25_sparse_text, build_canonical_content, canonicalize_cert_row
from app.rag.ingest.dlq import append_ingest_dlq
from app.rag.ingest.metadata import build_chunk_metadata
from app.services.vector_service import vector_service

logger = logging.getLogger(__name__)


@dataclass
class ReindexStats:
    rows: int = 0
    chunks: int = 0
    updated: int = 0
    skipped: int = 0
    sparse_patched: int = 0


def _iter_qualification_rows(limit: Optional[int] = None) -> List[Dict]:
    """
    qualification + certificates_vectors LEFT JOIN으로
    written_cnt/practical_cnt(exam_type 정확도), cert_summary/cert_description(content 품질),
    related_majors(도메인 태깅)를 함께 조회.

    RAG_CANONICAL_NCS_CSV=False(기본)이면 ncs_large_mapped·ncs_mid 컬럼을 SELECT하지 않는다.
    - canonical/BM25는 DB ncs_large만 사용(레거시 파이프라인과 동일).
    - 아직 해당 컬럼 마이그레이션이 없는 DB에서도 재색인이 실패하지 않게 한다.
    """
    db = SessionLocal()
    try:
        use_csv_ncs = bool(getattr(get_rag_settings(), "RAG_CANONICAL_NCS_CSV", False))
        ncs_csv_cols = (
            "q.ncs_large_mapped,\n                q.ncs_mid,\n                "
            if use_csv_ncs
            else ""
        )
        sql = f"""
            SELECT
                q.qual_id,
                q.qual_name,
                q.qual_type,
                q.main_field,
                q.ncs_large,
                {ncs_csv_cols}q.managing_body,
                q.grade_code,
                q.written_cnt,
                q.practical_cnt,
                cv.cert_summary,
                cv.cert_description,
                cv.related_majors
            FROM qualification q
            LEFT JOIN certificates_vectors cv
                ON q.qual_id = cv.qual_id AND cv.chunk_index = 0
            WHERE q.qual_name IS NOT NULL AND TRIM(q.qual_name) != ''
            ORDER BY q.qual_id
        """
        if limit and limit > 0:
            sql += " LIMIT :limit"
            rows = db.execute(text(sql), {"limit": int(limit)}).mappings().all()
        else:
            rows = db.execute(text(sql)).mappings().all()
        out = [dict(r) for r in rows]
        if not use_csv_ncs:
            for d in out:
                d.setdefault("ncs_large_mapped", None)
                d.setdefault("ncs_mid", None)
        logger.info(
            "reindex rows loaded: count=%s limit=%s RAG_CANONICAL_NCS_CSV=%s",
            len(out),
            limit,
            use_csv_ncs,
        )
        return out
    except Exception:
        logger.exception("failed to fetch qualification rows")
        raise
    finally:
        db.close()


def reindex_cert_vectors(
    *,
    limit: Optional[int] = None,
    batch_size: int = 128,
    chunk_profile: str = "baseline",
    dry_run: bool = False,
    debug: bool = False,
) -> ReindexStats:
    if debug:
        logger.setLevel(logging.DEBUG)
    started_at = time.perf_counter()
    rows = _iter_qualification_rows(limit=limit)
    stats = ReindexStats(rows=len(rows))
    if not rows:
        logger.info("reindex skipped: no rows")
        return stats

    db = SessionLocal()
    try:
        logger.info(
            "reindex started: rows=%s batch_size=%s profile=%s dry_run=%s",
            stats.rows,
            batch_size,
            chunk_profile,
            dry_run,
        )
        pending_batch: List[Dict] = []
        for row_idx, row in enumerate(rows, start=1):
            try:
                qual_id = int(row["qual_id"])
                qual_name = str(row.get("qual_name") or "").strip() or f"qual:{qual_id}"

                # related_majors: DB 조인값 → 리스트 변환 (문자열이면 split, None이면 빈 리스트)
                raw_majors = row.get("related_majors")
                if isinstance(raw_majors, str):
                    related_majors = [m.strip() for m in raw_majors.split(",") if m.strip()]
                elif isinstance(raw_majors, list):
                    related_majors = raw_majors
                else:
                    related_majors = []

                canonical = canonicalize_cert_row(dict(row), related_majors=related_majors)
                content = build_canonical_content(canonical)
                canonical_meta = build_canonical_metadata_from_row(row, related_majors=related_majors)
                chunks = section_chunk_with_metadata(
                    full_content=content,
                    qual_name=qual_name,
                    section_type="overview",
                    profile=chunk_profile,
                )

                for idx, chunk_text in enumerate(chunks):
                    chash = hashlib.sha256(chunk_text.encode("utf-8")).hexdigest()[:32]
                    bm25_text = build_bm25_sparse_text(
                        qual_id,
                        qual_name,
                        chunk_text,
                        qual_type=row.get("qual_type"),
                        main_field=row.get("main_field"),
                        ncs_large=canonical.get("ncs_large"),
                        ncs_mid=(canonical.get("ncs_mid") or None) or None,
                        domain=canonical.get("domain"),
                        top_domain=canonical.get("top_domain"),
                        managing_body=row.get("managing_body"),
                        grade_code=row.get("grade_code"),
                        related_majors=related_majors,
                    )
                    chunk_meta = build_chunk_metadata(
                        qual_id=qual_id,
                        qual_name=qual_name,
                        qual_type=row.get("qual_type"),
                        main_field=row.get("main_field"),
                        ncs_large=canonical.get("ncs_large"),
                        managing_body=row.get("managing_body"),
                        grade_code=row.get("grade_code"),
                        section_type="overview",
                        chunk_index=idx,
                        written_cnt=row.get("written_cnt"),
                        practical_cnt=row.get("practical_cnt"),
                        chunk_hash=chash,
                        ncs_mid=canonical.get("ncs_mid") or None,
                        **canonical_meta,
                    )
                    pending_batch.append(
                        {
                            "qual_id": qual_id,
                            "chunk_index": idx,
                            "name": qual_name,
                            "content": chunk_text,
                            "dense_content": chunk_text,
                            "bm25_text": bm25_text,
                            "metadata": chunk_meta,
                        }
                    )
                    stats.chunks += 1

                    if len(pending_batch) >= batch_size:
                        if dry_run:
                            stats.updated += len(pending_batch)
                        else:
                            updated, skipped, sparse_patched = vector_service.upsert_vector_data_batch(
                                db, pending_batch
                            )
                            stats.updated += updated
                            stats.skipped += skipped
                            stats.sparse_patched += sparse_patched
                        logger.debug(
                            "reindex batch flushed: size=%s updated=%s skipped=%s row_idx=%s",
                            len(pending_batch),
                            stats.updated,
                            stats.skipped,
                            row_idx,
                        )
                        pending_batch.clear()
            except Exception:
                logger.exception(
                    "reindex row failed and skipped: row_idx=%s qual_id=%s",
                    row_idx,
                    row.get("qual_id"),
                )
                append_ingest_dlq(
                    stage="reindex_cert_vectors",
                    qual_id=row.get("qual_id"),
                    detail={"row_idx": row_idx, "error": "row_processing_failed"},
                )
                continue

        if pending_batch:
            if dry_run:
                stats.updated += len(pending_batch)
            else:
                try:
                    updated, skipped, sparse_patched = vector_service.upsert_vector_data_batch(
                        db, pending_batch
                    )
                    stats.updated += updated
                    stats.skipped += skipped
                    stats.sparse_patched += sparse_patched
                except Exception:
                    logger.exception("final batch upsert failed: batch_size=%s", len(pending_batch))
            pending_batch.clear()

        elapsed_ms = int((time.perf_counter() - started_at) * 1000)
        logger.info(
            "reindex completed: rows=%s chunks=%s updated=%s skipped=%s sparse_patched=%s elapsed_ms=%s",
            stats.rows,
            stats.chunks,
            stats.updated,
            stats.skipped,
            stats.sparse_patched,
            elapsed_ms,
        )
        return stats
    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--batch-size", type=int, default=128)
    parser.add_argument("--chunk-profile", type=str, default="baseline")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()

    out = reindex_cert_vectors(
        limit=(args.limit or None),
        batch_size=max(int(args.batch_size), 1),
        chunk_profile=(args.chunk_profile or "baseline"),
        dry_run=bool(args.dry_run),
        debug=bool(args.debug),
    )
    print(
        f"reindex done: rows={out.rows} chunks={out.chunks} updated={out.updated} skipped={out.skipped} sparse_patched={out.sparse_patched}"
    )


if __name__ == "__main__":
    main()
