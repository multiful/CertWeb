-- ILIKE '%...%' 검색 가속: pg_trgm + GIN 인덱스
-- Supabase SQL Editor 또는 psql에서 실행 (한 번만)

CREATE EXTENSION IF NOT EXISTS pg_trgm;

CREATE INDEX IF NOT EXISTS idx_qualification_qual_name_gin
ON qualification USING GIN (qual_name gin_trgm_ops);

CREATE INDEX IF NOT EXISTS idx_qualification_managing_body_gin
ON qualification USING GIN (managing_body gin_trgm_ops);
