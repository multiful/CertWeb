
export interface SemanticSearchResult {
    qual_id: number;
    qual_name: string;
    qual_type: string | null;
    main_field: string | null;
    managing_body: string | null;
    similarity_score: number;
}

export interface SemanticSearchResponse {
    query: string;
    results: SemanticSearchResult[];
}

export interface HybridRecommendationResult {
    qual_id: number;
    qual_name: string;
    semantic_similarity: number;
    interest_level?: number;           // 1~9 관심도 레벨 (UI용)
    major_score: number;
    reason: string | null;
    hybrid_score: number;
    pass_rate?: number | null;       // 최신 합격률 (0–100)
    rrf_score?: number | null;       // Reciprocal Rank Fusion 점수
    llm_reason?: boolean;            // GPT가 이유를 생성했으면 true
    /** 0~1 정규화, 전공 연관성 바용 */
    major_score_normalized?: number | null;
    /** 0~1 정규화, 관심도 일치 바용 (관심사-자격증 시멘틱 유사도) */
    semantic_score_normalized?: number | null;
}

export interface HybridRecommendationResponse {
    mode: string;
    major: string;
    interest?: string;
    results: HybridRecommendationResult[];
    guest_limited?: boolean;
    /** "current" | "enhanced" */
    rag_mode?: string;
    /** "bm25_vector_contrastive_rrf" | "vector_fulltext_rrf" — 검색 파이프라인 표시용 */
    retrieval_pipeline?: string | null;
}

export interface TrendingQualification {
    qual_id: number;
    qual_name: string;
    qual_type: string | null;
    main_field: string | null;
    score: number;
}

export interface TrendingQualificationListResponse {
    items: TrendingQualification[];
    total: number;
}
