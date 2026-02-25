-- Extension in Public 경고 해소: pgvector를 extensions 스키마로 이동
-- 실행 전 백업 권장. 실행 후 기존 vector 타입 사용 쿼리는 그대로 동작합니다.
-- (컬럼 타입은 내부 OID로 저장되며, search_path에 extensions가 없으면
--  새로 vector 타입을 쓰는 DDL에서 extensions.vector 로 명시하거나
--  DB 기본 search_path에 extensions 추가 필요할 수 있음)

CREATE SCHEMA IF NOT EXISTS extensions;

ALTER EXTENSION vector SET SCHEMA extensions;
