# RAG/AI Recommendation Enhancement Plan

This document outlines the roadmap for upgrading the current static recommendation system to a dynamic RAG (Retrieval-Augmented Generation) based system.

## 1. Architectural Overview
The goal is to move beyond static mapping and enable semantic understanding of user intent and certification content.

### Current State
- Join based on `major_qualification_map`.
- Limited to pre-defined mappings.

### Future State (RAG)
- **Vector Store**: Use Supabase `pgvector` to store embeddings of certification titles, descriptions, and exam subjects.
- **Embedding Model**: Utilize OpenAI's `text-embedding-3-small` or HuggingFace models for Korean text embedding.
- **Retrieval**: Perform semantic search based on user's specific interests (e.g., "I want to work in cloud security").
- **Generation (LLM)**: Use GPT-4o or Claude 3.5 Sonnet to explain the recommendation in natural language.

## 2. Implementation Steps

### Phase 1: Data Preparation
1.  **Enrich Data**: Scrape or extract detailed "exam subjects" and "job descriptions" for each certification.
2.  **Generate Embeddings**: Create a script to embed the gathered text and store it in a `vector` column in the `qualifications` table.
3.  **Indexing**: Create an HNSW index on the vector column for fast retrieval.

### Phase 2: Backend API Upgrade
1.  **New Endpoint**: `POST /api/v1/recommendations/ai`
2.  **Semantic Search Logic**:
    - Embed the user query.
    - Perform a vector similarity search (cosine similarity).
    - Combine results with traditional "Major" filtering (Hybrid Search).
3.  **LLM Integration**:
    - Pass the top-N certifications and user profile to an LLM.
    - Prompt: "Based on the user's major in X and interest in Y, explain why these 3 certifications are the best fit."

### Phase 3: Frontend Integration
1.  **AI Chat Interface**: Add a floating AI assistant or a "Ask AI" tab in the Recommendation page.
2.  **Dynamic Explanations**: Display the LLM-generated reasons instead of static database strings.

## 3. Benefits
- **Higher Relevance**: Handles niche or cross-disciplinary queries.
- **Natural Language**: Users can describe their goals in their own words.
- **Personalization**: Explanations are tailored to the user's unique profile.

## 4. Next Actions
- Verify the Supabase PostgreSQL instance has `pgvector` extension enabled.
- Begin embedding data for IT-related certifications as a pilot.
