-- RLS Disabled in Public 경고 해소
-- Supabase SQL Editor에서 한 번 실행. 배포(PostgREST) 노출 스키마에 RLS 적용.
-- 실행 시 "Potential issue detected / Query has destructive operation" 경고가 나올 수 있음.
-- 이 스크립트는 RLS 활성화 및 정책 추가만 하며, 데이터를 지우지 않습니다. 의도한 실행이면 "Run this query" 선택.
--
-- [certificates_vectors 테이블] RAG(벡터 검색)에서 사용하므로 테이블은 삭제하지 마세요.
-- 샘플 행만 지우려면: DELETE FROM certificates_vectors WHERE metadata->>'source' = 'verification_script';
-- 전체 비우고 DB 기준으로 다시 채우려면: scripts/populate_certificates_vectors.py --truncate 실행.

-- 1) 참조용 공개 테이블: 누구나 읽기만 허용 (anon, authenticated)
ALTER TABLE IF EXISTS public.major ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.qualification ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.qualification_stats ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.major_qualification_map ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.qualification_job_map ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.job ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "public_read_major" ON public.major;
CREATE POLICY "public_read_major" ON public.major FOR SELECT TO anon, authenticated USING (true);

DROP POLICY IF EXISTS "public_read_qualification" ON public.qualification;
CREATE POLICY "public_read_qualification" ON public.qualification FOR SELECT TO anon, authenticated USING (true);

DROP POLICY IF EXISTS "public_read_qualification_stats" ON public.qualification_stats;
CREATE POLICY "public_read_qualification_stats" ON public.qualification_stats FOR SELECT TO anon, authenticated USING (true);

DROP POLICY IF EXISTS "public_read_major_qualification_map" ON public.major_qualification_map;
CREATE POLICY "public_read_major_qualification_map" ON public.major_qualification_map FOR SELECT TO anon, authenticated USING (true);

DROP POLICY IF EXISTS "public_read_qualification_job_map" ON public.qualification_job_map;
CREATE POLICY "public_read_qualification_job_map" ON public.qualification_job_map FOR SELECT TO anon, authenticated USING (true);

DROP POLICY IF EXISTS "public_read_job" ON public.job;
CREATE POLICY "public_read_job" ON public.job FOR SELECT TO anon, authenticated USING (true);

-- 2) profiles: 로그인 사용자만 자신 행 읽기/수정, 가입 시 자신 행 삽입
ALTER TABLE IF EXISTS public.profiles ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "profiles_select_own" ON public.profiles;
CREATE POLICY "profiles_select_own" ON public.profiles FOR SELECT TO authenticated USING (id = auth.uid());

DROP POLICY IF EXISTS "profiles_update_own" ON public.profiles;
CREATE POLICY "profiles_update_own" ON public.profiles FOR UPDATE TO authenticated USING (id = auth.uid()) WITH CHECK (id = auth.uid());

DROP POLICY IF EXISTS "profiles_insert_own" ON public.profiles;
CREATE POLICY "profiles_insert_own" ON public.profiles FOR INSERT TO authenticated WITH CHECK (id = auth.uid());

-- 3) user_favorites: 본인 user_id 행만 CRUD (user_id = auth.uid() 또는 profiles.userid)
ALTER TABLE IF EXISTS public.user_favorites ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "user_favorites_own" ON public.user_favorites;
CREATE POLICY "user_favorites_own" ON public.user_favorites
  FOR ALL TO authenticated
  USING (
    user_id = auth.uid()::text
    OR user_id = (SELECT userid FROM public.profiles WHERE id = auth.uid() LIMIT 1)
  )
  WITH CHECK (
    user_id = auth.uid()::text
    OR user_id = (SELECT userid FROM public.profiles WHERE id = auth.uid() LIMIT 1)
  );

-- 4) user_acquired_certs: 동일
ALTER TABLE IF EXISTS public.user_acquired_certs ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "user_acquired_certs_own" ON public.user_acquired_certs;
CREATE POLICY "user_acquired_certs_own" ON public.user_acquired_certs
  FOR ALL TO authenticated
  USING (
    user_id = auth.uid()::text
    OR user_id = (SELECT userid FROM public.profiles WHERE id = auth.uid() LIMIT 1)
  )
  WITH CHECK (
    user_id = auth.uid()::text
    OR user_id = (SELECT userid FROM public.profiles WHERE id = auth.uid() LIMIT 1)
  );

-- 5) certificates_vectors: RLS만 켜고 정책 없음 → anon/authenticated는 접근 불가, 백엔드(service_role·직접연결)만 접근
ALTER TABLE IF EXISTS public.certificates_vectors ENABLE ROW LEVEL SECURITY;
-- (백엔드가 DATABASE_URL 또는 service_role로 접근하므로 RLS를 우회해 정상 동작)
