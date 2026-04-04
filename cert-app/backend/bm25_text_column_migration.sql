-- Indexing_opt.md: Hybrid용 sparse(BM25) 전용 컬럼 text_for_sparse
-- 적용 후: python -m app.rag index (또는 BM25 인덱스 빌드) 재실행

ALTER TABLE certificates_vectors
  ADD COLUMN IF NOT EXISTS bm25_text TEXT;

COMMENT ON COLUMN certificates_vectors.bm25_text IS
  'BM25 역색인 전용 문자열(qual_id·시행기관·등급·청크 본문). Dense content와 분리.';
