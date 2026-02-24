-- 의료기기RA전문가 2급(공인): qualification_stats에 합격률·응시자수 반영 (이미지 2급 공인 기준)
-- 기존 행이 있으면 갱신, 없으면 삽입. 다른 컬럼/다른 자격증은 변경하지 않음.

INSERT INTO qualification_stats (
  qual_id,
  year,
  exam_round,
  candidate_cnt,
  pass_cnt,
  pass_rate
)
SELECT
  q.qual_id,
  v.year,
  1 AS exam_round,
  v.candidate_cnt,
  v.pass_cnt,
  v.pass_rate
FROM qualification q
CROSS JOIN (
  VALUES
    (2024, 1798, 372, 20.69),
    (2023, 1315, 212, 16.12),
    (2022, 1373, 320, 23.31)
) AS v(year, candidate_cnt, pass_cnt, pass_rate)
WHERE q.qual_name LIKE '의료기기RA전문가%2급%'
   OR q.qual_name = '의료기기RA전문가 2급'
ON CONFLICT (qual_id, year, exam_round)
DO UPDATE SET
  candidate_cnt = EXCLUDED.candidate_cnt,
  pass_cnt      = EXCLUDED.pass_cnt,
  pass_rate     = EXCLUDED.pass_rate;
