-- dense_slot_labels: 재질의 슬롯 보조용 (intent_labels와 별도, slot_type별 라벨 임베딩)
-- 앱 코드: app/rag/utils/slot_vector_labels.py → lookup_slot_label_with_vector
-- 지원 slot_type: domain | difficulty | job | purpose | major
--
-- Supabase/Postgres에 적용 후 RAG_DENSE_SLOT_VECTOR_FALLBACK_ENABLE=True 로 켜서 사용.

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS dense_slot_labels (
    id SERIAL PRIMARY KEY,
    slot_type TEXT NOT NULL CHECK (slot_type IN ('domain', 'difficulty', 'job', 'purpose', 'major')),
    label_text TEXT NOT NULL,
    embedding vector(1536),
    active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS dense_slot_labels_slot_type_idx ON dense_slot_labels (slot_type);
CREATE INDEX IF NOT EXISTS dense_slot_labels_active_idx ON dense_slot_labels (active) WHERE active = true;

COMMENT ON TABLE dense_slot_labels IS
  'Dense 재질의 보정: slot_type별 정답 라벨 텍스트와 embedding. qualification 벡터와는 별개(슬롯 라벨 전용).';

-- 데이터 적재 후(행 수 > 1000 권장) ivfflat/hnsw 인덱스 생성:
-- CREATE INDEX ... ON dense_slot_labels USING hnsw (embedding vector_cosine_ops);
