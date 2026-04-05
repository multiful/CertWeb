-- qualification: CSV(NCS 매핑) 조인 컬럼
-- Supabase SQL Editor 또는 psql 에서 1회 실행 후 apply_ncs_mapping / 재인덱싱.

ALTER TABLE qualification
  ADD COLUMN IF NOT EXISTS ncs_large_mapped VARCHAR(200),
  ADD COLUMN IF NOT EXISTS ncs_mid VARCHAR(200);

COMMENT ON COLUMN qualification.ncs_large_mapped IS 'ncs_mapping 대직무분류(정규화·중점)';
COMMENT ON COLUMN qualification.ncs_mid IS 'ncs_mapping 중직무분류(정규화·중점)';
