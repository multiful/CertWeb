-- Supabase Dashboard 경고 해소: Function Search Path Mutable
-- 1) update_modified_column 은 vector_migration.sql 에서 CREATE OR REPLACE 시 SET search_path 적용됨.
-- 2) 아래는 대시보드에서 생성된 트리거 함수들에 search_path 고정 적용 (한 번만 실행).
--
-- [Leaked Password Protection] 은 코드로 해결 불가. Supabase 대시보드에서 설정:
--   Authentication → Providers → Email → "Enable leaked password protection" 활성화
--   (유출된 비밀번호 목록과 대조해 안전한 비밀번호만 허용)

-- handle_new_user: 가입 시 프로필 생성 트리거 (Supabase Auth 연동)
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_proc p JOIN pg_namespace n ON p.pronamespace = n.oid WHERE n.nspname = 'public' AND p.proname = 'handle_new_user') THEN
        EXECUTE 'ALTER FUNCTION public.handle_new_user() SET search_path = public';
    END IF;
END $$;

-- handle_profile_deleted: 프로필 삭제 시 연동 처리
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_proc p JOIN pg_namespace n ON p.pronamespace = n.oid WHERE n.nspname = 'public' AND p.proname = 'handle_profile_deleted') THEN
        EXECUTE 'ALTER FUNCTION public.handle_profile_deleted() SET search_path = public';
    END IF;
END $$;
