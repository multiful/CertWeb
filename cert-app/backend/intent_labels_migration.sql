-- intent_labels: 재질의 보정용 라벨 + 임베딩 (OpenAI text-embedding-3-small 등 1536차원)
-- kind 예시: job, purpose, major, domain, top_domain (앱: intent_vector_labels.lookup_intent_labels_with_vector)
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

COMMENT ON TABLE intent_labels IS
  '재질의 슬롯 보정: kind=job|purpose|major|domain|top_domain 등. 쿼리 임베딩과 코사인 근접 라벨 매칭. 자격증 청크 검색은 certificates_vectors/qualification.embedding 사용.';
