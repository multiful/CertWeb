# CertWeb 보안 및 Supabase 설정 검토 리포트

**검토 일자**: 2025-02-24  
**최종 업데이트**: 2025-02-24 (체크리스트·반영 상태 정리)  
**범위**: `cert-app/backend` (config, auth, deps, api), `cert-app/frontend` (supabase 클라이언트, useAuth, env), `.env.example` 및 설정 가이드

---

## 수정 시 필요한 정보 (참고·추가 도메인 시)

아래 항목은 **이미 코드에 반영**되어 있습니다. 신규 배포 도메인 추가·수신 이메일 변경 시 해당 환경 변수만 수정하면 됩니다.

| # | 항목 | 용도 | 반영 상태 | 비고 |
|---|------|------|-----------|------|
| 1 | **CORS 허용 도메인** | `main.py` → `CORS_ORIGINS`(쉼표 구분). 비어 있으면 기본값 사용. | ✅ 반영 | 기본: cert-web-sand.vercel.app, localhost:3000, 127.0.0.1:3000, 5173 |
| 2 | **문의 수신 이메일** | `contact.py` → `CONTACT_EMAIL`. 없으면 fallback 사용. | ✅ 반영 | |
| 3 | **Auth 전용 레이트 리밋** | `deps.check_auth_rate_limit` → send_code, verify_code, login, password_reset, signup_complete, **find_userid_send_code, find_userid_verify**. 분당 횟수. | ✅ 반영 | `AUTH_RATE_LIMIT_REQUESTS=5`, `AUTH_RATE_LIMIT_WINDOW=60` |
| 4 | **Supabase RLS 정책** | 대시보드 RLS 설정 여부 문서화. | ⚠️ 미설정 | 현재: **미설정**. 백엔드가 DATABASE_URL로 직접 접근하므로 Supabase 클라이언트로 직접 테이블 조회 시에만 RLS 영향. |

---

## 1. 보안 검토

### 1.1 환경 변수 / 시크릿 노출

| 구분 | 항목 | 심각도 | 내용 |
|------|------|--------|------|
| ✅ | `.env.example` Redis 예시 | **조치 완료** | 주석의 비밀번호 형태 문자열 삭제, REDIS_URL 플레이스홀더(`redis://default:<PASSWORD>@<REDIS_HOST>:<PORT>`)로 통일 완료. |
| ✅ | 백엔드 시크릿 로딩 | 통과 | `config.py`에서 `pydantic_settings` + `.env` 사용, `extra="ignore"`로 예기치 않은 키 무시. 실제 시크릿은 `.env`(gitignore)에만 두는 구조 적절. |
| ⚠️ | 프론트엔드 공개 값 | 경고 | `VITE_*` / `NEXT_PUBLIC_*`는 빌드 시 번들에 포함되므로 **anon key만** 사용. Service Role Key는 백엔드 전용으로 사용 중이며 프론트에 없음 → 적절. |
| ⚠️ | `config.py` 기본값 | 권장 | `DATABASE_URL` 기본값에 `password` 문자열 포함. 로컬 개발용이지만, 문서에 “프로덕션에서는 반드시 .env로 덮어쓸 것” 명시 권장. |

---

### 1.2 CORS, 인증/인가, 레이트 리밋

| 구분 | 항목 | 심각도 | 내용 |
|------|------|--------|------|
| ✅ | CORS | **조치 완료** | `main.py`에서 `settings.CORS_ORIGINS`(쉼표 구분)로 읽음. 비어 있으면 기본값(cert-web-sand.vercel.app, localhost:3000/5173 등) 사용. |
| ✅ | 인증 (JWT) | 통과 | `get_current_user_from_token`(auth 라우터)은 Supabase `/auth/v1/user`로 토큰 검증. `deps.get_current_user`는 JWKS(RS256/ES256) 또는 JWT_SECRET(HS256)으로 검증. 이중 검증 경로가 있으나 둘 다 유효. |
| ✅ | 인가 (관리자) | 통과 | Admin API는 `X-Job-Secret` + `verify_job_secret`로 보호. `JOB_SECRET` 미설정 시 503 반환. |
| ✅ | Auth 라우터 레이트 리밋 | **조치 완료** | `/auth/*` 전 구간 `check_rate_limit` + **Auth 전용** `check_auth_rate_limit`(분당 5회) 적용. send_code, verify_code, login, password_reset, signup_complete, **find-userid/send-code, find-userid/verify**에 한해 더 낮은 한도 적용됨. |
| ✅ | 아이디 찾기 보안 | **조치 완료** | 이메일만으로 아이디 노출 제거. **2단계**: (1) `POST /auth/find-userid/send-code` → 해당 이메일이 가입되어 있을 때만 Supabase OTP 발송, (2) `POST /auth/find-userid/verify` → 인증 코드 검증 후에만 userid 반환. 이메일 소유자만 아이디 확인 가능. |
| ✅ | 비밀번호 찾기 | **조치 완료** | Supabase `POST /auth/v1/recover` 사용. 재설정 링크가 이메일로 발송되며, 사용자가 링크에서 새 비밀번호 설정. 프론트: 이메일 입력 모달 → `POST /auth/password-reset` 호출. |

**수정 제안 (완료)**

- ~~CORS 환경 변수 이전~~ → **완료**: `CORS_ORIGINS` 환경 변수 반영됨.

---

### 1.3 사용자 입력 검증, SQL/NoSQL 인젝션

| 구분 | 항목 | 심각도 | 내용 |
|------|------|--------|------|
| ✅ | Auth 스키마 | 통과 | `EmailStr`, `userid` 패턴 `^[a-zA-Z0-9_]+$`, `min_length`/`max_length`, `password`/`password_confirm` 검증 등 Pydantic으로 적절히 제한. |
| ✅ | Auth 로그인 페이로드 | **조치 완료** | `AuthLoginRequest`: `userid` max 64자, `password` max 512자. `find_userid`: `email` Query max 320자. |
| ✅ | SQL 인젝션 | 통과 | `auth.py`, `certs.py`, `recommendations.py`, `ai_recommendations.py` 등에서 `text(...)` + named params(`:email`, `:uid` 등) 사용. 컬럼명은 `auth.py` update_profile에서 화이트리스트(`local_fields`)로만 구성 → 안전. |
| ✅ | NoSQL | 해당 없음 | PostgreSQL + Redis 사용. Redis 키/값은 코드에서 고정 패턴 또는 정수/문자열 조합으로만 생성. |

**수정 제안 (완료)**

- ~~AuthLoginRequest / find_userid 길이 상한~~ → **완료**: 스키마·Query에 `max_length` 적용됨.

---

### 1.4 민감 로그

| 구분 | 항목 | 심각도 | 내용 |
|------|------|--------|------|
| ⚠️ | Supabase/OTP 응답 로깅 | 경고 | `logger.error(f"Supabase OTP error: {res.text}")`, `logger.error(f"Supabase recovery error: {res.text}")` 등. `res.text`에 토큰·에러 상세가 포함될 수 있음. 상태 코드와 필요 시 요약만 로깅 권장. |
| ✅ | 토큰/비밀번호 직접 로깅 | 통과 | `password`, `access_token` 등을 로그에 직접 넣는 코드 없음. |
| ✅ | contact 수신 이메일 | **조치 완료** | `contact.py`에서 `CONTACT_EMAIL` 환경 변수 사용. 없으면 fallback 사용. |
| ✅ | Supabase API 에러 로깅 | **조치 완료** | `auth.py`에서 OTP/recovery/업데이트/생성 실패 시 `res.text` 대신 `status_code`만 로깅. |

---

## 2. Supabase 검토

### 2.1 연결 설정 (URL, anon key, service role 사용처)

| 구분 | 항목 | 내용 |
|------|------|------|
| ✅ | URL/키 소스 | 백엔드: `config.Settings`(SUPABASE_URL, SUPABASE_ANON_KEY, SUPABASE_SERVICE_ROLE_KEY, SUPABASE_JWT_SECRET). 프론트: `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY`만 사용. |
| ✅ | Service Role 사용처 | `app/api/auth.py`의 `_admin_headers()`에서만 사용. Admin API(사용자 생성/수정/삭제, 메타데이터) 호출에만 제한 → 적절. |
| ✅ | Anon Key | 프론트: Supabase 클라이언트 초기화. 백엔드: OTP/verify/recover, 토큰 검증(`/auth/v1/user`), 로그인(`/auth/v1/token`) 등. RLS와 함께 사용되는 공개 키로 사용처 적절. |

---

### 2.2 Auth 설정 (이메일/비밀번호, JWT 검증 흐름)

| 구항목 | 내용 |
|--------|------|
| ✅ | 이메일/비밀번호 | 가입: OTP → verify → signup-complete(백엔드에서 Admin API로 사용자 생성/비밀번호 설정). 로그인: userid → 로컬 DB에서 email 조회 → Supabase `/auth/v1/token?grant_type=password` 호출. |
| ✅ | JWT 검증 | 1) auth 라우터: `get_current_user_from_token` → Supabase `/auth/v1/user`로 검증. 2) favorites 등: `get_current_user`(deps) → `_decode_supabase_token`으로 HS256(JWT_SECRET) 또는 RS256/ES256(JWKS) 검증. |
| ✅ | 토큰-이메일 일치 | `signup-complete`에서 `token_email != payload.email`이면 403 반환. |

---

### 2.3 RLS, pgvector/DB 접근 권한

| 구분 | 항목 | 내용 |
|------|------|------|
| ⚠️ | RLS | **현재 미설정.** 프로젝트 내 RLS 정책 정의 파일 없음. 백엔드는 **DATABASE_URL**로 PostgreSQL 직접 접근, 프론트는 Supabase **Auth만** 사용 → DB 접근은 전부 백엔드 경유. RLS는 Supabase 클라이언트로 테이블 직접 조회 시에만 영향. |
| ✅ | pgvector | 벡터 검색은 백엔드 `text()` + 파라미터 바인딩으로만 수행. 클라이언트가 pgvector에 직접 접근하지 않음. |

**권장**

- Supabase 대시보드에서 `profiles` 등 테이블에 RLS 적용 시, 정책 요약을 이 문서에 반영.

---

### 2.4 프론트엔드 Supabase 클라이언트 초기화

| 구분 | 항목 | 내용 |
|------|------|------|
| ✅ | 초기화 방식 | `lib/supabase.ts`에서 `createClient(supabaseUrl, supabaseAnonKey, { auth: { storage: localStorage, persistSession: true, autoRefreshToken: true, detectSessionInUrl: true, flowType: 'pkce' } })`. PKCE 사용으로 인증 코드 노출 위험 감소. |
| ✅ | env 부재 시 | URL/키가 비어 있거나 URL이 `http`로 시작하지 않으면 mock 클라이언트 반환. 화면 크래시 방지용으로 적절. |
| ⚠️ | env 키 일관성 | `VITE_SUPABASE_*`와 `NEXT_PUBLIC_SUPABASE_*` 폴백 존재. 프로젝트가 Vite 기준이면 `NEXT_PUBLIC_*`는 제거해도 됨(혼동 방지). |
| ✅ | useAuth | `getSession` + `onAuthStateChange`로 세션/토큰 동기화. 토큰은 API 호출 시 Bearer로만 전달. |

---

## 3. 요약: 심각/경고/권장

### 심각 → 조치 완료

1. ~~**Auth 라우터 레이트 리밋 부재**~~ → **완료**: `/auth/*` 전 구간 `check_rate_limit` + Auth 전용 `check_auth_rate_limit`(5회/분) 적용.
2. ~~**`.env.example` 시크릿/인프라 노출**~~ → **완료**: Redis 비밀번호/호스트 플레이스홀더화 완료.

### 경고 → 조치 완료

3. ~~**CORS 하드코딩**~~ → **완료**: `CORS_ORIGINS` 환경 변수로 관리.
4. ~~**문의 수신 이메일 하드코딩**~~ → **완료**: `CONTACT_EMAIL` 환경 변수 반영.

### 경고 → 조치 완료

5. ~~**민감 로그**~~ → **완료**: `auth.py`에서 Supabase OTP/recovery/업데이트/생성 실패 시 `res.text` 대신 `status_code`만 로깅하도록 수정.

### 권장 → 조치 완료

6. ~~**로그인 페이로드 길이 제한**~~ → **완료**: `AuthLoginRequest`에 `userid` max 64자, `password` max 512자. `find_userid`에 `email` Query max 320자 적용.

7. **Supabase RLS**  
   - **문서화 완료**(미설정 명시). 정책 적용 시 Supabase 대시보드에서 수행.

---

## 4. 체크리스트 (배포 전)

| 완료 | 항목 | 비고 |
|:---:|------|------|
| ✅ | `.env.example`에서 실제 비밀번호/호스트 제거·플레이스홀더화 | |
| ✅ | Auth 라우터 전 구간 레이트 리밋 적용 | 전역 + Auth 전용(5회/분) |
| ✅ | CORS를 환경 변수로 관리 | `CORS_ORIGINS` (비어 있으면 기본값) |
| ✅ | 문의 수신 이메일 `CONTACT_EMAIL` 분리 | 없으면 fallback |
| ✅ | RAG 검색에 `match_threshold` 적용 | `RAG_MATCH_THRESHOLD`(기본 0.4) |
| ✅ | Auth API 에러 시 `res.text` 대신 상태 코드만 로깅 | `auth.py`: OTP/recovery/업데이트/생성 실패 시 `status_code`만 로깅 |
| ✅ | `AuthLoginRequest`·`find_userid`에 `max_length` 추가 | `userid` 64자, `password` 512자, `email` 320자 상한 |
| ✅ | Supabase RLS 정책 문서화 | **미설정** 상태 문서화 완료. 정책 적용 시 Supabase 대시보드에서 수행 |
| ⬜ | 프로덕션에서 `DEBUG=False`, `JOB_SECRET` 설정 확인 | **배포 시에만 가능**: .env 점검. 코드로 자동 검증 불가(환경별로 값 상이) |

**미완료 항목 설명**

- **프로덕션 DEBUG/JOB_SECRET**: 프로덕션 배포 전 담당자가 `.env`에서 `DEBUG=False`, `JOB_SECRET` 설정 여부를 확인하는 **운영 점검** 항목입니다. 코드에서 "프로덕션" 여부를 구분해 자동 검증할 수 없으므로, 체크리스트에서는 "배포 시 점검"으로 두고 배포 전 수동 확인이 필요합니다. (이미 `main.py` startup 시 `JOB_SECRET` 미설정 경고는 출력됨.)

---

## 5. RAG 검토 (Advanced RAG Engine 기준)

검토 기준: [advanced-rag-engine] 스킬 — Chunking, Embedding, Hybrid Search, Re-ranking, pgvector, 컨텍스트 주입 최적화.

### 5.1 현재 구현 요약

| 구분 | 현재 상태 | 스킬 권장 |
|------|-----------|-----------|
| **Embedding 모델** | `text-embedding-3-small`, 1536차원 (`app/utils/ai.py`) | ✅ 동일 모델·차원 권장과 일치 |
| **벡터 저장소** | PostgreSQL + pgvector. `qualification.embedding`, `certificates_vectors` 테이블 | ✅ 스키마에 `vector(1536)`, 코사인 거리 사용 |
| **인덱스** | `certificates_vectors`: ivfflat (`vector_cosine_ops`). `qualification`: embedding 컬럼 인덱스 여부는 DB 마이그레이션 확인 필요 | ⚠️ 스킬은 HNSW(m=16, ef_construction=64) 권장. ivfflat은 대용량에서 유효 |
| **검색** | `vector_service.similarity_search`: 코사인 유사도 + `match_threshold` 필터. `certs.py` `/search/rag`: 벡터 + Redis 트래픽 스코어 퓨전. `ai_recommendations`: 전공·관심사 임베딩 + DB 매핑 하이브리드 | ⚠️ 키워드 FTS(tsvector+GIN) 없음. RRF 공식 미적용(단순 가산점 결합) |
| **Re-ranking** | 없음. 후보 2~3배 검색 후 Cross-Encoder/LLM 재순위화 없음 | ❌ 스킬 권장: 20~30 후보 → Re-ranker → 상위 5~8개만 주입 |
| **Chunking** | `law_update_pipeline`: JSON 변경 1건 = 1청크. `certificates_vectors`: qual_id+name+content 단위. `qualification`: 행 단위 1 embedding. **RecursiveCharacterTextSplitter 등 체계적 청킹 없음** | ❌ 스킬: chunk_size=512, overlap=50, separators `["\n\n","\n"," ",""]` 권장 |
| **컨텍스트 주입** | `match_threshold`로 저관련 청크 제거. **`/search/rag`에서 `RAG_MATCH_THRESHOLD` 적용 완료.** 순서는 유사도(및 트래픽) 기반 | ✅ 관련성 높은 청크만 주입·순서 유지 충족 |

### 5.2 체크리스트 (스킬 기준)

- [ ] **Chunk overlap**으로 경계 정보 손실 최소화 — 현재 문서 단위/행 단위 저장, overlap 없음.
- [ ] **Re-ranking**으로 노이즈 청크 필터링 — 미구현.
- [x] 프롬프트에 **관련성 높은 청크만** 주입 — **반영 완료**: `rag_search`에서 `RAG_MATCH_THRESHOLD`(기본 0.4) 사용.
- [x] 청크 순서: 관련성 순 반환 — 유사도(및 퓨전 스코어) 순 정렬됨.
- [ ] **메타데이터**(출처, 제목)를 프롬프트에 포함 — `certificates_vectors.metadata`는 있으나, 검색 결과를 LLM에 넘기는 흐름에서 메타데이터 포함 여부는 사용처에 따름.

### 5.3 개선 제안 (우선순위)

1. **단기**  
   - ✅ **반영 완료**: `certs.py`의 `rag_search`에서 `vector_service.similarity_search(..., match_threshold=settings.RAG_MATCH_THRESHOLD)` 적용. `config.RAG_MATCH_THRESHOLD`(기본 0.4)로 저관련 청크 제거.  
   - (선택) `certificates_vectors`에 `fts tsvector` + GIN 인덱스 추가 후, 키워드 검색과 **FTS+RRF**로 하이브리드 검색 구현.

2. **중기**  
   - 인덱싱 시 **RecursiveCharacterTextSplitter** 도입: 긴 `content`를 chunk_size=512, overlap=50, separators `["\n\n","\n"," ",""]`로 분할 후 저장.  
   - **Re-ranking**: 초기 20~30개 후보 검색 → 유사도/스코어 상위 5~8개만 LLM/API 응답에 사용.

3. **장기**  
   - **HNSW** 인덱스 검토 (데이터 규모 증가 시).  
   - **Recall@k / MRR** 등 검색 품질 지표 수집·평가.

---

## 6. 최종 연결 검토

아래는 RAG·설정·API·프론트 연결이 일관되게 동작하는지 정리한 요약입니다.

| 구간 | 연결 내용 | 상태 |
|------|-----------|------|
| **CORS** | `main.py` → `settings.CORS_ORIGINS`(쉼표 구분) → 배포 URL·localhost | ✅ 환경 변수 반영 |
| **문의** | `contact.py` → `CONTACT_EMAIL`(없으면 fallback) | ✅ 환경 변수 반영 |
| **Auth 레이트 리밋** | `deps.check_auth_rate_limit` → `auth.py` (send_code, verify_code, login, password_reset, signup_complete) | ✅ 분당 5회 적용 |
| **RAG 검색** | `GET /api/v1/certs/search/rag` → `vector_service.similarity_search(..., match_threshold=RAG_MATCH_THRESHOLD)` → `certificates_vectors` | ✅ match_threshold 적용 |
| **RAG 설정** | `config.RAG_MATCH_THRESHOLD`(기본 0.4), `.env`에서 `RAG_MATCH_THRESHOLD`로 오버라이드 가능 | ✅ |
| **임베딩** | `vector_service` / `ai_recommendations` → `app.utils.ai.get_embedding` → OpenAI | ✅ 레이턴시·토큰 로깅 있음 |
| **벡터 저장** | `law_update_pipeline` → `vector_service.upsert_vector_data` → `certificates_vectors` | ✅ |
| **프론트 검색** | 자격증 목록: `GET /certs?q=...`(키워드). RAG 고급 검색: `GET /certs/search/rag`는 프론트에서 직접 호출하지 않음(API만 노출) | ⚠️ 필요 시 프론트에서 RAG 검색 UI 연동 가능 |

**정리**: 설정(CORS, CONTACT_EMAIL, Auth 레이트 리밋, RAG_MATCH_THRESHOLD)은 모두 코드에 반영되어 있으며, RAG 단기 개선(match_threshold)이 적용된 상태입니다. 중기·장기 개선(RecursiveCharacterTextSplitter, Re-ranking, HNSW, Recall@k)은 추후 단계로 문서에 명시되어 있습니다.

---

## 7. 데이터 프로파일링 (MLOps Data Profiler 기준)

RAG/벡터 관련 데이터 품질·규모를 확인하기 위한 프로파일링 스크립트와 검토 요약입니다.

### 7.1 프로파일링 스크립트

| 항목 | 내용 |
|------|------|
| **위치** | `cert-app/backend/scripts/data_profile_rag.py` |
| **실행** | `cert-app/backend`에서 `uv run python scripts/data_profile_rag.py` (DB 연결 필요) |
| **대상** | `certificates_vectors`(행 수, content 길이 min/max/avg/median, embedding NULL 수), `qualification`(행 수, qual_name 길이, embedding NULL 수) |
| **원칙** | 벡터화된 집계 쿼리만 사용(row-wise loop 없음), 스키마·이상치 요약 출력 |

### 7.2 검토 요약 (스킬 체크리스트)

- **벡터화**: 프로파일링은 SQL 집계 1회로 수행, 반복 연산 회피.
- **스키마**: `certificates_vectors`(vector_id, qual_id, name, content, embedding, metadata), `qualification`(qual_id, qual_name, …, embedding) — Pydantic은 API 레이어에서 사용 중.
- **이상치**: content/qual_name 길이 0 또는 극단적 max는 스크립트 출력으로 확인 후 필요 시 제거/캡 정책 적용.
- **AI 추론 모니터링**: `app.utils.ai`의 `get_embedding`에서 `latency_ms`, `input_tokens` 로깅 적용됨 (`_log_embedding_usage`). LLM 채팅 호출(예: law_update_pipeline, ai_recommendations)은 필요 시 동일 패턴으로 토큰/레이턴시 추적 권장.

---

## 문서 개선 이력

| 날짜 | 내용 |
|------|------|
| 2025-02-24 | 초안: 보안·Supabase·RAG 검토, 체크리스트, 연결 검토, 데이터 프로파일링 섹션 추가. |
| 2025-02-24 | 체크리스트 반영: CORS/CONTACT_EMAIL/Auth 레이트 리밋/RAG match_threshold 반영 완료 표시. RLS 미설정 명시. §3 요약·§4 체크리스트 표 형식으로 정리. |
| 2025-02-24 | 체크리스트 수행: 민감 로그(auth.py status_code만 로깅), AuthLoginRequest·find_userid max_length 적용. RLS 문서화 완료. 미완료 1건(프로덕션 DEBUG/JOB_SECRET)은 배포 시 점검으로 유지·사유 명시. |
