# API Update Summary

The following FastAPI endpoints have been implemented based on the "Recommendation Logic SQL Design".

## 1. Job-Based Recommendations (Job -> Certifications)
**Endpoint:** `GET /api/v1/recommendations/jobs/{job_id}/certifications`

Returns certifications that are required or helpful for a specific job.

**SQL Logic Implemented:**
```sql
SELECT 
    q.qual_name, q.main_field, j.job_name,
    j.entry_salary, j.outlook_summary
FROM qualification q
JOIN qualification_job_map qjm ON q.qual_id = qjm.qual_id
JOIN job j ON qjm.job_id = j.job_id
WHERE j.job_id = :job_id
ORDER BY q.qual_type ASC
```

## 2. Certification-Based Career Paths (Certification -> Jobs)
**Endpoint:** `GET /api/v1/recommendations/certifications/{qual_id}/jobs`

Returns jobs that can be pursued with a specific certification, ordered by salary score.

**SQL Logic Implemented:**
```sql
SELECT 
    j.job_name, j.reward, j.stability, j.development
FROM job j
JOIN qualification_job_map qjm ON j.job_id = qjm.job_id
WHERE qjm.qual_id = :qual_id
ORDER BY j.reward DESC
LIMIT 5
```

## 3. Pass Rate Trends (Detailed Stats)
**Endpoint:** `GET /api/v1/certs/{qual_id}/trends`

Returns pass rate trends for the last 3 years to analyze difficulty.

**SQL Logic Implemented:**
```sql
SELECT year, exam_round, pass_rate, difficulty_score
FROM qualification_stats
WHERE qual_id = :qual_id AND year >= (current_year - 3)
ORDER BY year DESC, exam_round DESC
```

## Usage Note
These endpoints execute **Direct SQL Queries** against the configured PostgreSQL database. Ensure your database connection is active and populated with data for these endpoints to return results.
