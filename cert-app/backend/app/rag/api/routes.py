"""
POST /rag/ask: question, filters, baseline_id, top_k → answer, citations, debug(scores)
"""
import hashlib
import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.deps import get_db_session, check_rate_limit
from app.rag.config import get_rag_settings
from app.rag.retrieve.hybrid import hybrid_retrieve, _fetch_contents_by_chunk_ids
from app.rag.retrieve.cache import get_cached_rag_response, set_cached_rag_response
from app.rag.rerank.cross_encoder import rerank_with_cross_encoder
from app.rag.generate.evidence_first import generate_evidence_first_answer
from app.rag.generate.gating import check_gating
from app.rag.index.vector_index import get_vector_search
from app.utils.rag_hybrid import enhanced_rag_03_hybrid
from app.utils.ai import get_embedding

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/rag", tags=["rag"])


class RAGAskRequest(BaseModel):
    question: str = Field(..., min_length=1)
    filters: Optional[Dict[str, Any]] = None
    baseline_id: str = Field(default="enhanced_reranker", description="baseline | current | current_reranker | enhanced_reranker")
    top_k: int = Field(default=4, ge=1, le=20)


class RAGAskResponse(BaseModel):
    answer: str
    citations: List[str]
    evidence_bullets: Optional[List[str]] = None
    gating_applied: bool = False
    suggested_questions: Optional[List[str]] = None
    debug: Optional[Dict[str, Any]] = None


def _chunk_ids_to_contents(
    db: Session,
    chunk_ids_with_scores: List[tuple],
) -> List[tuple]:
    """
    (chunk_id, content, score) 리스트.
    content는 hybrid 모듈의 _fetch_contents_by_chunk_ids를 통해 한 번에 조회해 DB I/O를 최소화한다.
    """
    if not chunk_ids_with_scores:
        return []
    chunk_ids = [cid for cid, _ in chunk_ids_with_scores]
    contents = _fetch_contents_by_chunk_ids(db, chunk_ids)
    rows: List[tuple] = []
    for cid, score in chunk_ids_with_scores:
        rows.append((cid, contents.get(cid, "") or "", score))
    return rows


@router.post("/ask", response_model=RAGAskResponse)
async def rag_ask(
    body: RAGAskRequest,
    db: Session = Depends(get_db_session),
    _: None = Depends(check_rate_limit),
):
    """RAG 질의: baseline_id에 따라 벡터만/현재 hybrid/고도화 hybrid+rerank+gating."""
    settings = get_rag_settings()
    question = (body.question or "").strip()
    if not question:
        raise HTTPException(400, "question required")

    cache_key_id = hashlib.sha256(question.encode()).hexdigest()[:16]
    cached = get_cached_rag_response(
        question,
        filters=body.filters,
        top_k=body.top_k,
        baseline_id=body.baseline_id,
    )
    if cached and isinstance(cached, dict):
        return RAGAskResponse(**cached)

    chunk_ids_with_scores: List[tuple] = []
    if body.baseline_id == "baseline":
        vector_results = get_vector_search(db, question, top_k=body.top_k, threshold=None)
        chunk_ids_with_scores = [(r[0], r[1]) for r in vector_results]
    elif body.baseline_id == "current":
        vec = get_embedding(question)
        qual_ids = enhanced_rag_03_hybrid(db, question, vec, body.top_k)
        chunk_ids_with_scores = [(f"{qid}:0", 1.0) for qid in qual_ids]
    elif body.baseline_id == "current_reranker":
        # Current RRF 후보, 상위 20 pool + Cross-Encoder 리랭커 → Top4
        vec = get_embedding(question)
        pool = 20
        qual_ids = enhanced_rag_03_hybrid(db, question, vec, pool)
        chunk_ids_with_scores = [(f"{qid}:0", 1.0) for qid in qual_ids]
        chunks_pre = _chunk_ids_to_contents(db, chunk_ids_with_scores)
        pairs = [(cid, content) for cid, content, _ in chunks_pre]
        reranked = rerank_with_cross_encoder(question, pairs, top_k=body.top_k)
        if reranked:
            chunk_ids_with_scores = reranked
        else:
            chunk_ids_with_scores = chunk_ids_with_scores[: body.top_k]
    elif body.baseline_id == "enhanced_reranker":
        # RRF Top30 후보, 상위 20 pool + Cross-Encoder Reranker → Top4 (BM25+Vector hybrid)
        candidates = hybrid_retrieve(db, question, top_k=body.top_k, filters=body.filters, use_reranker=True)
        chunk_ids_with_scores = [(c[0], c[1]) for c in candidates]
    else:
        # baseline: 벡터만
        vector_results = get_vector_search(db, question, top_k=body.top_k, threshold=None)
        chunk_ids_with_scores = [(r[0], r[1]) for r in vector_results]

    chunks_with_content = _chunk_ids_to_contents(db, chunk_ids_with_scores)
    if not chunks_with_content:
        chunks_with_content = [(cid, "", s) for cid, s in chunk_ids_with_scores]

    top1_score = chunk_ids_with_scores[0][1] if chunk_ids_with_scores else 0.0
    gate = check_gating(top1_score, chunks_with_content, question)
    logger.debug(
        "rag_ask retrieval summary (baseline_id=%s top1_score=%.6f chunk_count=%d)",
        body.baseline_id,
        top1_score,
        len(chunk_ids_with_scores),
    )
    if gate.applied:
        resp_dict = {
            "answer": gate.answer,
            "citations": [],
            "evidence_bullets": None,
            "gating_applied": True,
            "suggested_questions": gate.suggested_questions,
            "debug": {
                "top1_score": top1_score,
                "chunk_count": len(chunk_ids_with_scores),
                "baseline_id": body.baseline_id,
            },
        }
        set_cached_rag_response(question, resp_dict, filters=body.filters, top_k=body.top_k, baseline_id=body.baseline_id)
        return RAGAskResponse(
            answer=gate.answer,
            citations=[],
            gating_applied=True,
            suggested_questions=gate.suggested_questions,
            debug={"top1_score": top1_score, "chunk_count": len(chunk_ids_with_scores)},
        )

    answer, evidence_bullets, citation_ids = generate_evidence_first_answer(
        question,
        chunks_with_content,
        max_evidence=min(6, len(chunks_with_content)),
    )
    response = RAGAskResponse(
        answer=answer,
        citations=citation_ids,
        evidence_bullets=evidence_bullets,
        gating_applied=False,
        debug={
            "top1_score": top1_score,
            "chunk_count": len(chunk_ids_with_scores),
            "baseline_id": body.baseline_id,
        },
    )
    set_cached_rag_response(
        question,
        response.model_dump(mode="json"),
        filters=body.filters,
        top_k=body.top_k,
        baseline_id=body.baseline_id,
    )
    return response
