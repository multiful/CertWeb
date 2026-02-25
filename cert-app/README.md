# Cert-App (프로젝트명: 안티그래비티)

**"무중력 속도(Ultra-low Latency)로 경험하는 맞춤형 자격증 추천 플랫폼"**

안티그래비티(Anti-gravity) 프로젝트는 방대한 자격증 데이터를 가장 빠르고 정확하게 탐색하고, 사용자 전공 및 선호도에 맞춰 지능적으로 추천해주는 웹 서비스입니다. 
대한민국 **1,000여 종**의 국가 기술 및 전문 자격증 데이터를 실시간으로 분석합니다.

---

## 주요 기능 (Features)

1. **초저지연(Ultra-low Latency) 자격증 조회 시스템**
   - **Redis 직접 동기화 & 캐싱**: DB 조회 없이 1ms 내의 응답 제공
   - **orjson 직렬화**: FastAPI 엔드포인트에서 JSON 직렬화 오버헤드 극대화 억제
2. **AI 기반 자격증 맞춤 추천 (Vector DB)**
   - **pgvector & Supabase**: 자격증 요약 텍스트 임베딩을 이용한 시맨틱 유사도 검색
   - **OpenAI API**: 사용자 전공과 관심사를 분석하여 가장 적합한 트랙 제안
3. **취득 자격증 & XP·레벨·티어 시스템**
   - **취득 자격증 (Acquired Certs)**: 사용자가 취득한 자격증을 DB 목록에서 검색해 등록·관리 (`user_acquired_certs` 테이블)
   - **난이도 기반 XP**: `app/utils/xp.py` — 자격증 난이도(1.0~9.9) 구간별 가중치 적용, 최소 0.5 XP 보장
   - **9단계 레벨·티어**: Lv1~2 Bronze, Lv3~4 Silver, Lv5~6 Gold, Lv7~8 Platinum, Lv9 Diamond (solved.ac 스타일 보석 색상)
   - **레벨 게이지바**: 마이페이지 ACQUIRED CERTS 카드 및 "내가 취득한 자격증" 섹션에서 티어·XP·다음 레벨 진행률 시각화
4. **인증 및 보안 (Auth & Security)**
   - **Professional Inactivity Session Management**: 1시간 이상 비활동 시 자동 로그아웃 구현
   - **Supabase Auth**: 안전한 JWT 기반 세션 관리 (자체 DB 연동 백업)
5. **모던 UI/UX (Frontend)**
   - 최신 **React + Vite** 아키텍처 사용
   - **TailwindCSS + Shadcn UI** 조합으로 빠르고 직관적인 사용자 경험 제공
   - 마이페이지: 취득 자격증 목록 + XP 뱃지, 백엔드 summary 미제공 시 프론트엔드 로컬 XP/티어 계산 폴백

---

## 기술 스택 (Tech Stack)

### **Frontend**
- **Framework**: React 19, Vite 7 (초고속 빌드 및 HMR)
- **Styling**: Tailwind CSS, Shadcn UI (Radix UI 기반 컴포넌트)
- **State Management**: Context, Custom Hooks (`useAuth`, `useRecommendations`, `useMajors`, `usePopularMajors` 등)
- **API Client**: Fetch API + Custom Wrapper (`src/lib/api.ts` — Auto-retry, Mock Fallback)
- **Routing**: Client-side Router (`src/lib/router.tsx`)

### **Backend**
- **Framework**: FastAPI (Async 파이썬 웹 프레임워크)
- **Database**: PostgreSQL (Supabase)
- **ORM**: SQLAlchemy 2.x
- **Vector Search**: pgvector (Supabase)
- **Cache**: Redis (`redis-py` 싱글톤), `orjson` (초고속 JSON)
- **Authentication**: Supabase Auth (OTP, 이메일/비밀번호)
- **External API**: OpenAI API (AI 추천·시맨틱 검색)
- **기타**: GZip·TrustedHost·CORS 미들웨어, Rate limiting, Admin API (`X-Job-Secret`)

---

## 프로젝트 구조 (Directory Structure)

```text
cert-app/
├── backend/                         # FastAPI 백엔드
│   ├── app/
│   │   ├── api/                     # API 라우터
│   │   │   ├── certs.py             # 자격증 검색·상세·통계·트렌딩·RAG 검색
│   │   │   ├── fast_certs.py        # Redis 기반 초저지연 목록
│   │   │   ├── recommendations.py  # 전공 기반 추천, /me, /majors, /popular-majors, jobs 연동
│   │   │   ├── ai_recommendations.py # AI 하이브리드 추천·시맨틱 검색
│   │   │   ├── auth.py              # Supabase Auth, 프로필·OTP
│   │   │   ├── acquired_certs.py   # 취득 자격증·XP·summary
│   │   │   ├── favorites.py         # 즐겨찾기
│   │   │   ├── jobs.py              # 직무 목록·상세
│   │   │   ├── majors.py            # 전공 목록
│   │   │   ├── admin.py             # Admin API (X-Job-Secret)
│   │   │   ├── contact.py           # 문의/피드백 메일
│   │   │   └── deps.py              # DB 세션, rate limit, 인증 의존성
│   │   ├── schemas/                 # Pydantic 스키마
│   │   ├── services/
│   │   │   ├── data_loader.py       # CSV 기반 자격증 데이터 로더
│   │   │   ├── fast_sync_service.py # DB → Redis 전체 동기화
│   │   │   ├── vector_service.py    # pgvector 임베딩·유사도 검색
│   │   │   ├── law_update_pipeline.py # 법령/자격 요약 파이프라인
│   │   │   └── email_service.py     # 문의 메일 발송
│   │   ├── utils/                   # xp.py(레벨·티어), ai.py, auth.py, stream_producer.py
│   │   ├── config.py, database.py, crud.py, models.py
│   │   ├── redis_client.py          # 캐시·레이트리밋
│   │   ├── redis_sync_worker.py     # cert_updates 구독 동기화
│   │   └── scheduler.py
│   ├── scripts/
│   │   └── populate_certificates_vectors.py   # RAG용 certificates_vectors 채우기
│   ├── main.py
│   ├── init.sql                     # 스키마·샘플 데이터
│   ├── vector_migration.sql         # pgvector·certificates_vectors
│   ├── rename_production_automation_names.sql
│   ├── update_medical_device_ra_stats.sql
│   ├── requirements.txt
│   ├── run.ps1                      # Windows: uvicorn 실행 (venv 경로 지정)
│   └── Dockerfile
├── frontend/
│   └── app/                         # Vite + React 앱
│       ├── src/
│       │   ├── components/          # UI (Shadcn), Layout, ChunkLoadError
│       │   ├── hooks/               # useAuth, useRecommendations, useMajors, usePopularMajors
│       │   ├── pages/               # Home, CertList, CertDetail, Recommendation, JobDetail, MyPage 등
│       │   ├── lib/                 # api.ts, router.tsx, mockApi.ts, utils
│       │   └── types/               # API 타입·추천 타입
│       ├── package.json
│       ├── vite.config.ts
│       ├── tsconfig.*.json
│       └── index.html
└── docker-compose.yml               # backend, frontend, db, redis
```

---

## 설치 및 실행 (Setup & Run)

### 1. 환경 변수 설정
```bash
# 백엔드
cp backend/.env.example backend/.env
# 필요 시 DATABASE_URL, REDIS_URL, SUPABASE_*, OPENAI_API_KEY 등 수정

# 프론트엔드
cp frontend/app/.env.example frontend/app/.env
# VITE_API_BASE_URL 등 수정
```

### 2. 백엔드 실행
```bash
cd backend
# 가상환경 생성 후 (선택) pip install -r requirements.txt
# 또는 uv 사용 시:
uv run uvicorn main:app --reload
# Windows에서 run.ps1 사용 시 (venv 경로 지정):
./run.ps1
```
- 기본 포트: **8000**  
- API 문서: `http://localhost:8000/docs` (DEBUG=True 시)  
- 헬스: `GET /health`

### 3. 프론트엔드 실행
```bash
cd frontend/app
npm install
npm run dev
```
- 기본 포트: **5173** (Vite)
- 빌드: `npm run build` (tsc -b && vite build)

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
평균 난이도(5.0) 자격증 1개 ≈ 5 XP → Lv2 Bronze 도달.

---

## Redis 캐시 작동 원리

이 서비스는 가장 빠른 사용자 경험을 제공하기 위해 **자격증 조회**를 극단적으로 최적화했습니다.

1. **데이터 갱신 (Producer)**: 자격증 테이블에 CRUD가 발생할 경우 Redis Pub/Sub 채널(`cert_updates`)로 메시지 발행.
2. **실시간 싱크 (Sync Worker)**: 초경량 Python 워커가 채널을 구독하여 즉시 데이터를 orjson으로 직렬화해 Redis RAM 캐시에 꽂아넣습니다. (`app/redis_sync_worker.py`)
3. **가장 빠른 반환 (FastAPI Endpoint)**: 사용자가 앱에서 조회를 요청하면 백엔드(`app/api/fast_certs.py`)는 미들웨어나 모델 파싱조차 건너뛰고, Redis 비동기 풀(Pool)에서 원시 데이터를 꺼내 그대로 브라우저로 쏘아보냅니다.

---

## 기타 API 요약
- **자격증**: `GET /api/v1/certs`, `GET /api/v1/certs/{id}`, `GET /api/v1/certs/trending/now`, `GET /api/v1/certs/search/rag`
- **추천**: `GET /api/v1/recommendations?major=...`, `GET /api/v1/recommendations/me`, `GET /api/v1/recommendations/majors`, `GET /api/v1/recommendations/popular-majors`
- **AI**: `GET /api/v1/recommendations/ai/hybrid-recommendation`, `GET /api/v1/recommendations/ai/semantic-search`
- **직무**: `GET /api/v1/jobs`, `GET /api/v1/jobs/{id}`
- **인증**: `GET /api/v1/auth/profile`, `PATCH /api/v1/auth/profile`, OTP·로그인·회원가입 등
- **문의**: `POST /api/v1/contact`

## 이슈 트래킹 및 기여 (Troubleshooting & Contribution)
- 회원가입 인증 시 `check constraint "chk_userid_len"` 등 글자 수 제한이 걸리면, Supabase SQL Editor에서 해당 제약을 조정할 수 있습니다.
- JWT 검증은 `app/utils/auth.py`에서 Supabase `/auth/v1/user` REST API에 위임해 호환성을 맞춥니다.
- **시퀀스 중복 오류**: 대량 import 후 `qualification` 등 SERIAL 시퀀스가 꼬리면, `SELECT SETVAL(pg_get_serial_sequence('public.qualification','qual_id'), (SELECT MAX(qual_id) FROM qualification)+1);` 로 동기화합니다.
