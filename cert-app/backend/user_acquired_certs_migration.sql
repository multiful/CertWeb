-- 취득 자격증 테이블 (Profile 사용자별). Supabase/PostgreSQL 동일 스키마 사용.
-- 실행: psql $DATABASE_URL -f user_acquired_certs_migration.sql

CREATE TABLE IF NOT EXISTS user_acquired_certs (
    acq_id SERIAL PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    qual_id INTEGER NOT NULL REFERENCES qualification(qual_id) ON DELETE CASCADE,
    acquired_at DATE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(user_id, qual_id)
);

CREATE INDEX IF NOT EXISTS idx_acquired_certs_user ON user_acquired_certs(user_id);
CREATE INDEX IF NOT EXISTS idx_acquired_certs_qual ON user_acquired_certs(qual_id);

COMMENT ON TABLE user_acquired_certs IS '사용자별 취득 자격증. user_id는 auth(JWT sub)와 동일.';
