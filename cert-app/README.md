# Cert-App

**" 맞춤형 자격증 추천 플랫폼"**

---

## 주요 기능 (Features)

1. **초저지연·캐시 기반 자격증 조회**
   - **Redis 캐싱**: 자격증 목록/상세/통계·필터 옵션·추천·RAG 검색 응답 캐시 (orjson 직렬화)
   - **Rate limiting**: Redis 기반 요청 제한 (일반·인증 전용)
   - **선택적 Fast path**: `fast_certs.py` — Redis 동기화 구독 시 초저지연 목록 응답 (Sync Worker 연동)
2. **AI 기반 자격증 맞춤 추천 (Hybrid RAG)**
   - **pgvector & Supabase**: `certificates_vectors` 임베딩 검색, BM25·Vector·Contrastive **다채널 융합**(Linear 기본), 선택적 Cross-Encoder 리랭킹
   - **OpenAI API**: 임베딩·dense query rewrite·(옵션) HyDE/CoT 등 확장 경로
   - **RAG 파이프라인**: `app/rag` — `hybrid_retrieve`, 메타/개인화 soft, 계층 BM25, Redis 캐시, evidence-first 생성
   - **기능 목록**: `backend/docs/RAG_FEATURES.md`
3. **취득 자격증 & XP·레벨·티어 시스템**
   - **취득 자격증 (Acquired Certs)**: DB 검색으로 등록·관리 (`user_acquired_certs`), 마이페이지 취득 자격증·XP 요약
   - **난이도 기반 XP**: `app/utils/xp.py` — 난이도 구간별 가중치, 최소 0.5 XP
   - **9단계 레벨·티어**: Lv1~2 Bronze → Lv9 Diamond (solved.ac 스타일), 레벨 게이지바 시각화
4. **인증 및 보안 (Auth & Security)**
   - **비활동 세션 관리**: 1시간 이상 비활동 시 자동 로그아웃
   - **Supabase Auth**: JWT 세션, OTP·이메일/비밀번호, 프로필·전공·학년
5. **모던 UI/UX (Frontend)**
   - **React + Vite**, TailwindCSS + Shadcn UI
   - **TanStack Query (React Query)**: 자격증 목록/상세/통계·필터 옵션 캐시(staleTime 10분·1시간)
   - 마이페이지: 취득 자격증, XP·티어, 관심·최근 본·전공 맞춤 추천, 세션/캐시 복원

---

## 기술 스택 (Tech Stack)

### **Frontend**
- **Framework**: React 19, Vite 7
- **Styling**: Tailwind CSS, Shadcn UI (Radix UI 기반)
- **State & Server State**: Context, TanStack Query (`useCerts`, `useCertDetail`, `useFilterOptions` 등), Custom Hooks (`useAuth`, `useRecommendations`, `useMajors`, `usePopularMajors`)
- **API Client**: Fetch + `src/lib/api.ts` (재시도, Mock Fallback)
- **Routing**: Client-side Router (`src/lib/router.tsx`)

### **Backend**
- **Framework**: FastAPI (Async)
- **Database**: PostgreSQL (Supabase)
- **ORM**: SQLAlchemy 2.x
- **Vector Search**: pgvector (Supabase), `certificates_vectors`
- **Cache & 공통**: Redis (`redis-py` 싱글톤, orjson), Rate limiting
- **Auth**: Supabase Auth (OTP, 이메일/비밀번호)
- **External API**: OpenAI API (임베딩·AI 추천·시맨틱·LLM 리랭킹)
- **기타**: GZip·TrustedHost·CORS, Admin API (`X-Job-Secret`), RAG reranker 캐시(Redis)

---

## 프로젝트 구조 (Directory Structure)

```text
cert-app/
├── backend/                         # FastAPI 백엔드
│   ├── app/
│   │   ├── api/                     # API 라우터
│   │   │   ├── certs.py             # 자격증 검색·상세·통계·트렌딩·RAG 검색·최근 본
│   │   │   ├── fast_certs.py        # Redis 기반 초저지연 목록 (선택)
│   │   │   ├── recommendations.py  # 전공 기반 추천, /me, /majors, /popular-majors, jobs 연동
│   │   │   ├── ai_recommendations.py # AI 하이브리드 추천·시맨틱 검색
│   │   │   ├── auth.py              # Supabase Auth, 프로필·OTP
│   │   │   ├── acquired_certs.py   # 취득 자격증·XP·summary
│   │   │   ├── favorites.py         # 즐겨찾기
│   │   │   ├── jobs.py              # 직무 목록·상세
│   │   │   ├── majors.py            # 전공 목록
│   │   │   ├── admin.py             # Admin API (X-Job-Secret), 캐시 무효화
│   │   │   ├── contact.py           # 문의/피드백 메일
│   │   │   └── deps.py              # DB 세션, rate limit, 인증 의존성
│   │   ├── rag/                     # RAG 파이프라인
│   │   │   ├── retrieve/            # hybrid(BM25+Vector+Contrastive), RRF, 메타데이터 필터
│   │   │   ├── rerank/              # Cross-Encoder API, 캐시(Redis·LRU)
│   │   │   ├── generate/            # evidence-first 답변 생성, gating
│   │   │   ├── index/               # BM25 인덱스 빌더, vector_index
│   │   │   ├── eval/                # 골든 평가, retrieval/generation 메트릭
│   │   │   ├── api/routes.py        # RAG 질의 엔드포인트
│   │   │   ├── config.py            # RAG_TOP_N, RERANK_POOL_SIZE 등
│   │   │   └── utils/               # query 처리, dense rewrite, golden 매핑
│   │   ├── schemas/                 # Pydantic 스키마
│   │   ├── services/
│   │   │   ├── data_loader.py       # CSV 기반 자격증 데이터 로더
│   │   │   ├── fast_sync_service.py # DB → Redis 전체 동기화
│   │   │   ├── vector_service.py   # pgvector 임베딩·유사도 검색 (content/metadata 선택 조회)
│   │   │   ├── law_update_pipeline.py # 법령/자격 요약 파이프라인
│   │   │   └── email_service.py    # 문의 메일 발송
│   │   ├── utils/                   # xp.py(레벨·티어), ai.py, auth.py, stream_producer.py
│   │   ├── config.py, database.py, crud.py, models.py
│   │   ├── redis_client.py          # 캐시·레이트리밋·트렌딩·최근 본·RAG 캐시 키
│   │   ├── redis_sync_worker.py     # cert_updates 구독 동기화 (선택)
│   │   └── scheduler.py
│   ├── docs/                        # RAG_FEATURES.md, 성능·RAG 검토 문서
│   ├── main.py
│   ├── init.sql                     # 스키마·인덱스·샘플 데이터
│   ├── vector_migration.sql         # pgvector·certificates_vectors
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   └── app/                         # Vite + React 앱
│       ├── src/
│       │   ├── components/          # UI (Shadcn), Layout, ChunkLoadError
│       │   ├── hooks/               # useAuth, useCerts, useRecommendations, useMajors, usePopularMajors
│       │   ├── pages/               # Home, CertList, CertDetail, Recommendation, AiRecommendation, JobList, JobDetail, MyPage 등
│       │   ├── lib/                 # api.ts, router.tsx, queryKeys, mockApi.ts, utils
│       │   └── types/               # API·추천 타입
│       ├── package.json
│       ├── vite.config.ts
│       ├── tsconfig.*.json
│       └── index.html
└── docker-compose.yml               # backend, frontend, db, redis (선택)
```

---

## 취득 자격증 API & XP·레벨 로직

| 엔드포인트 | 설명 |
|------------|------|
| `GET /api/v1/me/acquired-certs` | 취득 자격증 목록 (페이지네이션, 각 항목에 `xp` 포함) |
| `GET /api/v1/me/acquired-certs/count` | 취득 개수만 반환 |
| `GET /api/v1/me/acquired-certs/summary` | total_xp, level, tier, current_level_xp, next_level_xp, cert_count |
| `POST /api/v1/me/acquired-certs/{qual_id}` | 취득 자격증 추가 (이미 있으면 기존 항목 반환) |
| `DELETE /api/v1/me/acquired-certs/{qual_id}` | 취득 자격증 제거 |

**XP 계산** (`app/utils/xp.py`): 자격증 난이도(1.0~9.9) 구간별 가중치 → `난이도 + 보너스` (최소 0.5).  
**레벨 임계값**: 0 → 5 → 15 → 35 → 70 → 120 → 190 → 290 → 430 XP (Lv1~9).

---

## Redis 사용 (캐시·레이트리밋·트렌딩)

Redis는 **캐시·레이트리밋·트렌딩·최근 본** 용도로 사용됩니다. (`app/redis_client.py`)

1. **API 응답 캐시 (orjson 직렬화)**
   - 자격증 목록/개수/상세/통계/필터 옵션 (`certs:list:v7`, `certs:count:v7`, `certs:detail:*`, `certs:stats:*` 등)
   - 추천 API (`recs:*`), RAG 검색 (`rag_ask:*`)
   - TTL: 목록/추천 10분, 상세/통계 1시간 등 설정 가능
2. **레이트 리밋**
   - 일반 API·인증 API별 분당 요청 제한 (Redis 카운터)
3. **트렌딩·최근 본**
   - `trending_certs` (Sorted Set): 상세 조회 시 점수 증가, 트렌딩 목록 조회
   - `user:{user_id}:recent_certs`: 로그인 사용자 최근 본 자격증 ID 목록
4. **선택: 실시간 동기화**
   - Pub/Sub 채널 `cert_updates` 구독 시 `redis_sync_worker.py`가 DB 변경을 Redis에 반영. `fast_certs.py`가 해당 캐시를 읽어 초저지연 목록 응답에 사용할 수 있음.

Redis 미연결 시 캐시·트렌딩·레이트리밋은 비활성화되고, DB 직접 조회로 동작합니다.

---

## 기타 API 요약

- **자격증**: `GET /api/v1/certs`, `GET /api/v1/certs/{id}`, `GET /api/v1/certs/trending/now`, `GET /api/v1/certs/search/rag`, `GET /api/v1/certs/recent/viewed`
- **추천**: `GET /api/v1/recommendations?major=...`, `GET /api/v1/recommendations/me`, `GET /api/v1/recommendations/majors`, `GET /api/v1/recommendations/popular-majors`
- **AI**: `GET /api/v1/recommendations/ai/hybrid-recommendation`, `GET /api/v1/recommendations/ai/semantic-search`
- **직무**: `GET /api/v1/jobs`, `GET /api/v1/jobs/{id}`
- **인증**: `GET /api/v1/auth/profile`, `PATCH /api/v1/auth/profile`, OTP·로그인·회원가입 등
- **문의**: `POST /api/v1/contact`

---

## 이슈 트래킹 및 트러블슈팅 (Troubleshooting)

- **회원가입·제약**: `check constraint "chk_userid_len"` 등 글자 수 제한은 Supabase SQL Editor에서 제약 조정 가능.
- **JWT 검증**: `app/utils/auth.py`에서 Supabase `/auth/v1/user` REST API에 위임.
- **시퀀스 중복**: 대량 import 후 `qualification` 등 SERIAL 시퀀스 꼬리면  
  `SELECT SETVAL(pg_get_serial_sequence('public.qualification','qual_id'), (SELECT MAX(qual_id) FROM qualification)+1);` 로 동기화.
- **성능·캐시·RAG**: RAG 스위치·모듈 전체는 `backend/docs/RAG_FEATURES.md`. 인덱싱은 `backend/RAG_Indexing.md`.
- **배포**: Vercel(프론트)·Railway(백엔드)·Supabase·Redis Cloud·환경변수는 `.cursor/rules/deployment.mdc` 참고.
