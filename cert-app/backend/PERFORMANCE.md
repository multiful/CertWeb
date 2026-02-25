# 속도 개선 요약

## 이미 적용된 사항

- **Redis 캐시**: 목록/상세/필터옵션/추천/인기전공/트렌딩/즐겨찾기 등 캐시 키별 TTL 적용.
- **Bulk 조회**: 자격 목록·즐겨찾기·취득자격 등에서 `get_qualification_aggregated_stats_bulk`로 N+1 제거, 청크(400) 단위로 바인드 파라미터 제한.
- **Fast API** (`/certs/{id}/fast`): aioredis + orjson, 50ms 타임아웃, Redis 미적중 시에만 DB 폴백.
- **추천**: `get_by_major_with_stats`에서 `joinedload(qualification).joinedload(stats)`로 1회 쿼리.
- **직렬화**: orjson 사용 (redis_client, fast_certs).
- **필터 옵션**: 4회 쿼리 → 1회 쿼리 후 Python에서 distinct 수집.
- **프론트**: 즐겨찾기 stats 보강 시 상세 API 호출 최대 10건으로 제한.

## 인덱스

- `qualification`: qual_name, qual_type, main_field, ncs_large, is_active, managing_body.
- `qualification_stats`: qual_id, year.
- `major_qualification_map`: major.
- `user_favorites` / `user_acquired_certs`: user_id, qual_id.
- `certificates_vectors`: ivfflat(embedding) (vector_migration.sql).

## 반영된 추가 개선

- **검색(ILIKE)**: `migrations/add_pg_trgm_gin_indexes.sql` — `pg_trgm` 확장 + `qual_name`, `managing_body` GIN 인덱스. Supabase SQL Editor에서 한 번 실행.
- **목록 count**: 동일 필터의 다른 페이지 요청 시 `query.count()` 생략. `certs:count:v5:{filter_hash}` 로 total 캐시, `get_list(..., cached_total=...)` 전달.
- **RAG**: `match_threshold` 를 DB WHERE `(embedding <=> :embedding) <= :max_distance` 로 적용해 임계값 미만 행은 DB에서 제외.
