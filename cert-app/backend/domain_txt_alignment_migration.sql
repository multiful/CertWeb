-- domain.txt 기준 도메인 정합성 마이그레이션
-- 기준: dataset/domain.txt
-- 목적:
-- 1) qualification.main_field(세부도메인) 기준 ncs_large(상위도메인) 정합
-- 2) certificates_vectors.domain 기준 domain_normalized 정합
--
-- 현재 확인된 불일치:
-- - 세부도메인 '의류/패션제작'의 상위도메인이 '크리에이티브/미디어'로 저장된 데이터
--   -> domain.txt 기준 '교육/생활서비스'로 교정

BEGIN;

-- qualification 정합
UPDATE qualification
SET
  ncs_large = '교육/생활서비스',
  updated_at = NOW()
WHERE main_field = '의류/패션제작'
  AND COALESCE(ncs_large, '') <> '교육/생활서비스';

-- certificates_vectors 정합
UPDATE certificates_vectors
SET
  domain_normalized = '교육/생활서비스',
  metadata = CASE
    WHEN metadata IS NULL THEN NULL
    ELSE jsonb_set(metadata, '{domain_normalized}', to_jsonb('교육/생활서비스'::text), true)
  END,
  updated_at = NOW()
WHERE domain = '의류/패션제작'
  AND COALESCE(domain_normalized, '') <> '교육/생활서비스';

COMMIT;
