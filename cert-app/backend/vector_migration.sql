-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Create certificates_vectors table
CREATE TABLE IF NOT EXISTS certificates_vectors (
    vector_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    qual_id INTEGER REFERENCES qualification(qual_id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    content TEXT NOT NULL,
    embedding VECTOR(1536), -- OpenAI text-embedding-3-small or similar
    metadata JSONB DEFAULT '{}'::jsonb,
    applied_date DATE DEFAULT CURRENT_DATE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index for vector search (Cosine Similarity)
-- Note: IVFFlat is good for large datasets. For smaller ones, HNSW is often preferred but IVFFlat is simpler to setup.
CREATE INDEX IF NOT EXISTS certificates_vectors_embedding_idx 
ON certificates_vectors USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- Trigger for updated_at
CREATE OR REPLACE FUNCTION update_modified_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ language 'plpgsql';

DROP TRIGGER IF EXISTS update_certificates_vectors_modtime ON certificates_vectors;
CREATE TRIGGER update_certificates_vectors_modtime
    BEFORE UPDATE ON certificates_vectors
    FOR EACH ROW
    EXECUTE PROCEDURE update_modified_column();
