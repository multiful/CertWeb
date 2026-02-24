import asyncio
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Optional
from app.api.deps import get_db_session, check_rate_limit, get_current_user
from app.utils.ai import get_embedding_async
import numpy as np

router = APIRouter(prefix="/recommendations/ai", tags=["ai-recommendations"])

@router.get("/semantic-search")
async def semantic_search(
    query: str = Query(..., description="Semantic search query (e.g., 'Cloud security career')"),
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db_session),
    _: None = Depends(check_rate_limit),
    user_id: str = Depends(get_current_user),
):
    """
    Perform semantic search using pgvector and OpenAI embeddings. 로그인 사용자 전용.
    """
    # 1. Embed user query using OpenAI
    query_vector = await get_embedding_async(query)
    
    # 2. Perform vector search using cosine similarity
    # <=> is the cosine distance operator in pgvector
    sql = text("""
        SELECT qual_id, qual_name, qual_type, main_field, managing_body,
               1 - (embedding <=> :vec) as similarity
        FROM qualification
        WHERE embedding IS NOT NULL
        ORDER BY embedding <=> :vec
        LIMIT :limit
    """)
    
    results = db.execute(sql, {"vec": str(query_vector), "limit": limit}).fetchall()
    
    formatted = []
    for r in results:
        formatted.append({
            "qual_id": r.qual_id,
            "qual_name": r.qual_name,
            "qual_type": r.qual_type,
            "main_field": r.main_field,
            "managing_body": r.managing_body,
            "similarity_score": float(r.similarity)
        })
        
    return {
        "query": query,
        "results": formatted
    }

@router.get("/hybrid-recommendation")
async def hybrid_recommendation(
    major: str = Query(..., description="User's major"),
    interest: Optional[str] = Query(None, description="Specific interests or career goals"),
    limit: int = Query(5, ge=1, le=20),
    db: Session = Depends(get_db_session),
    _: None = Depends(check_rate_limit),
    user_id: str = Depends(get_current_user),
):
    """
    Combines Major-based mapping with Semantic search (Hybrid Search). 로그인 사용자 전용.
    """
    # 1. Fetch certifications traditionally mapped to this major
    major_sql = text("""
        SELECT q.qual_id, q.qual_name, q.qual_type, q.main_field, mq.score as mapping_score, mq.reason
        FROM qualification q
        JOIN major_qualification_map mq ON q.qual_id = mq.qual_id
        WHERE mq.major = :major
        ORDER BY mq.score DESC
        LIMIT 50
    """)
    major_results = db.execute(major_sql, {"major": major}).fetchall()
    
    # 2 & 3. Global Semantic Search + Major vector — 병렬 임베딩 호출
    interest_vector, major_vector = await asyncio.gather(
        get_embedding_async(interest or major),
        get_embedding_async(major),
    )
    global_semantic_sql = text("""
        SELECT qual_id, qual_name,
               1 - (embedding <=> :vec) as similarity
        FROM qualification
        WHERE embedding IS NOT NULL
        ORDER BY embedding <=> :vec
        LIMIT 100
    """)
    global_results = db.execute(global_semantic_sql, {"vec": str(interest_vector)}).fetchall()

    # Dynamic Major Relevance (Semantic match between Major Name and Qualification)
    # This prevents the "0 or 90" problem by providing a continuous score
    major_sim_sql = text("""
        SELECT qual_id, 1 - (embedding <=> :vec) as major_sim
        FROM qualification
        WHERE embedding IS NOT NULL
    """)
    m_sims = db.execute(major_sim_sql, {"vec": str(major_vector)}).fetchall()
    major_sim_lookup = {r.qual_id: float(r.major_sim) for r in m_sims}

    # 4. Combine Candidates
    candidate_map = {}
    
    # Process major results from map
    for r in major_results:
        # Scale DB score (0-10) to 0.5-1.0 base if it exists, 
        # but also consider semantic similarity to major name
        m_sim = major_sim_lookup.get(r.qual_id, 0.5)
        # Use existing score if high, otherwise fallback to semantic
        base_major_score = max(float(r.mapping_score or 0), m_sim * 10.0)
        
        candidate_map[r.qual_id] = {
            "qual_id": r.qual_id,
            "qual_name": r.qual_name,
            "major_score": base_major_score,
            "reason": r.reason or "전공 맞춤형 자격증",
            "semantic_similarity": 0.0 
        }

    # Process interest results
    for r in global_results:
        m_sim = major_sim_lookup.get(r.qual_id, 0.3)
        if r.qual_id in candidate_map:
            candidate_map[r.qual_id]["semantic_similarity"] = float(r.similarity)
        else:
            # New candidate from interest
            candidate_map[r.qual_id] = {
                "qual_id": r.qual_id,
                "qual_name": r.qual_name,
                "major_score": m_sim * 10.0, # Purely semantic fallback
                "reason": "관심사 기반 연관 자격증",
                "semantic_similarity": float(r.similarity)
            }

    # 5. Final Hybrid Scoring & Thresholding
    final_results = []
    for cid, c in candidate_map.items():
        # Minimum relevance: must have some major link OR high interest similarity
        if c["major_score"] < 4.0 and c["semantic_similarity"] < 0.25:
            continue
            
        # Hybrid Score = 0.6 * Interest + 0.4 * Major
        h_score = (c["semantic_similarity"] * 0.6) + (c["major_score"] / 10.0 * 0.4)
        c["hybrid_score"] = h_score
        
        # Format reason more nicely
        if c["major_score"] > 8.0 and c["semantic_similarity"] > 0.4:
            c["reason"] = f"전공({major})과 매우 밀접하며, 관심사({interest})와도 높은 연관성을 보입니다."
        elif c["major_score"] > 7.0:
            c["reason"] = f"전공 분야의 핵심 역량을 증명할 수 있는 주요 자격증입니다."
        elif c["semantic_similarity"] > 0.5:
            c["reason"] = f"작성해주신 관심사({interest}) 분야에서 매우 인기 있는 전문 자격증입니다."
            
        final_results.append(c)

    # Sort by hybrid score
    sorted_results = sorted(final_results, key=lambda x: x['hybrid_score'], reverse=True)[:limit]

    return {
        "mode": "hybrid",
        "major": major,
        "interest": interest,
        "results": sorted_results
    }
