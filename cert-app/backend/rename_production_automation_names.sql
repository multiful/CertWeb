-- Rename legacy production automation qualifications to new official names
-- Run this once against the production database.

-- 산업기사: 생산자동화산업기사 -> 자동화설비산업기사
UPDATE qualification
SET qual_name = '자동화설비산업기사'
WHERE qual_name = '생산자동화산업기사';

-- 기능사: 생산자동화기능사 -> 자동화설비기능사
UPDATE qualification
SET qual_name = '자동화설비기능사'
WHERE qual_name = '생산자동화기능사';

-- If vector contents were seeded with the old names, keep them in sync as well.
UPDATE certificates_vectors
SET name = '자동화설비산업기사'
WHERE name = '생산자동화산업기사';

UPDATE certificates_vectors
SET name = '자동화설비기능사'
WHERE name = '생산자동화기능사';

