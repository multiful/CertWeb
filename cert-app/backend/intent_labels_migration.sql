-- intent_labels: 재질의 보정용 희망직무(job)/목적(purpose) 카테고리 (OpenAI embedding 1536)
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS intent_labels (
    id SERIAL PRIMARY KEY,
    kind TEXT NOT NULL,
    label TEXT NOT NULL,
    embedding vector(1536),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS intent_labels_kind_idx ON intent_labels (kind);
-- embedding 인덱스는 데이터 삽입 후 스크립트에서 생성 (빈 테이블에선 ivfflat 불가)

COMMENT ON TABLE intent_labels IS '재질의 슬롯 보정용: kind=job(희망직무), purpose(목적). label별 embedding으로 유사 쿼리 매칭.';
