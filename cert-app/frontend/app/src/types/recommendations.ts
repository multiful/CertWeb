
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
    major_score: number;
    reason: string | null;
    hybrid_score: number;
    pass_rate?: number | null;       // 최신 합격률 (0–100)
    rrf_score?: number | null;       // Reciprocal Rank Fusion 점수
    llm_reason?: boolean;            // GPT가 이유를 생성했으면 true
}

export interface HybridRecommendationResponse {
    mode: string;
    major: string;
    interest?: string;
    results: HybridRecommendationResult[];
    guest_limited?: boolean;
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
