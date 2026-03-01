# CertFinder (자격증파인더)

**대한민국 국가자격증 통합 분석 및 AI 경력 경로 추천 시스템**

[![Deploy: Vercel](https://img.shields.io/badge/Deploy-Vercel-black?style=flat-square&logo=vercel)](https://vercel.com/)
[![Backend: FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688?style=flat-square&logo=fastapi)](https://fastapi.tiangolo.com/)
[![DB: Supabase](https://img.shields.io/badge/DB-Supabase-3ECF8E?style=flat-square&logo=supabase)](https://supabase.com/)
[![Cache: Redis](https://img.shields.io/badge/Cache-Redis-DC382D?style=flat-square&logo=redis)](https://redis.io/)
[![API: Render](https://img.shields.io/badge/API-Render-46E3B7?style=flat-square&logo=render)](https://certweb-xzpx.onrender.com/health)

---

## 프로젝트 개요

**CertFinder**는 대한민국 **1,100여 종**의 국가 기술·전문 자격증 데이터를 실시간으로 분석해, 사용자에게 맞는 자격증과 직무 정보를 제공하는 웹 플랫폼입니다. 합격률·난이도·취업 전망과 함께 **전공 기반 AI 추천**, **직무 분석**, **북마크·취득 자격증 관리**까지 한 곳에서 이용할 수 있습니다.

| 환경 | URL |
|------|-----|
| **프론트엔드** | https://cert-web-multifuls-projects.vercel.app |
| **백엔드 API** | https://certweb-xzpx.onrender.com |
| **헬스 체크** | https://certweb-xzpx.onrender.com/health |

---

## 핵심 기능

### 1. 자격증 탐색

- **검색·필터**: 키워드, 분야(main_field), 자격 유형, 시행기관, 합격률 유무 등으로 필터링
- **페이지네이션**: 페이지당 20개, URL `?page=` 반영으로 뒤로가기 시 페이지 유지
- **북마크**: 관심 자격증 저장 (로그인 시)
- **취득 자격증 제외**: 로그인 사용자 — “취득 자격증 제외” 토글로 이미 취득한 항목 숨기기, 카드에 “취득” 뱃지 표시
- **상세 페이지**: 연도/회차별 합격률·난이도, Recharts 시각화, 연관 직무

### 2. 진로·직무 매칭

- **직무 목록**: 450여 개 직무의 전망·초임·역량 요약, 레이더 차트
- **페이지네이션**: 페이지당 20개, 이전/다음 + 1~5 번호 버튼, URL `?q=&page=` 동기화
- **직무 상세**: 핵심 적성·요구 역량, 취업 경로, 연관 자격증

### 3. AI 추천 (하이브리드 RAG)

- **전공 + 관심사 입력**: 전공명·커리어 목표 기반 추천
- **알고리즘**: Query Expansion(HyDE) → 전공 매핑 + 시멘틱 검색(pgvector) → RRF 융합 → 합격률·난이도 보정 → **LLM Cross-encoder 리랭킹** + 맞춤 이유 생성
- **퍼지 전공 매칭**: DB에 없는 전공명은 pg_trgm 유사도로 근접 전공 사용
- **취득 자격증 제외**: 로그인 시 이미 취득한 자격증은 추천 후보에서 제외
- **게스트**: 비로그인 시 결과 3개 제한; 로그인 시 더 많은 결과 + LLM 이유

### 4. 계정·마이페이지

- **인증**: Supabase Auth (이메일 OTP, Google OAuth)
- **마이페이지**: 닉네임·전공·학년, 북마크·취득 자격증, XP·레벨·티어
- **취득 자격증**: DB 자격증 검색 후 등록·삭제, XP 누적
- **문의하기**: Naver SMTP 이메일 발송 (Render 백그라운드)

### 5. 인프라·성능

- **Redis**: 직무/자격증 목록 등 캐시 (1시간 TTL)
- **Rate limiting**: IP 기반 요청 제한
- **CORS**: Bearer 인증 기반, `allow_origins=["*"]`, `allow_credentials=False`

---

## 기술 스택

| 영역 | 기술 |
|------|------|
| **Frontend** | React 19, TypeScript, Vite 7, Tailwind CSS, shadcn/ui (Radix), Recharts |
| **Backend** | FastAPI, SQLAlchemy 2, Pydantic v2, orjson |
| **DB** | PostgreSQL (Supabase), pgvector |
| **캐시** | Redis Cloud |
| **Auth** | Supabase Auth (JWT, Google OAuth) |
| **AI** | OpenAI text-embedding-3-small, GPT-4o-mini (쿼리 확장·리랭킹·이유 생성) |
| **배포** | Vercel (Frontend), Render (Backend) |
| **이메일** | Naver SMTP (문의 폼) |

---

## 디렉토리 구조

```
CertWeb/
├── cert-app/
│   ├── backend/                    # FastAPI
│   │   ├── app/
│   │   │   ├── api/                # 라우터 (certs, jobs, recommendations, ai_recommendations, contact, me, ...)
│   │   │   ├── crud/
│   │   │   ├── models.py
│   │   │   ├── schemas/
│   │   │   ├── utils/               # ai.py (embedding, query expansion, LLM rerank/reason)
│   │   │   └── services/
│   │   ├── main.py
│   │   ├── requirements.txt
│   │   └── scripts/                # populate_certificates_vectors.py 등
│   └── frontend/
│       └── app/                     # Vite + React
│           ├── src/
│           │   ├── pages/           # Home, CertList, CertDetail, JobList, JobDetail, AiRecommendation, MyPage, Contact, ...
│           │   ├── components/
│           │   ├── lib/             # api.ts, router, supabase
│           │   └── types/
│           ├── index.html
│           └── package.json
├── .cursor/rules/                  # 배포·uv·플러그인 규칙
└── README.md
```

---

## 시작하기 (로컬 개발)

### 사전 요구

- **Python 3.11+** (권장: `uv` 사용)
- **Node.js 18+**
- **Supabase / Redis** (또는 로컬 PostgreSQL + Redis)

### 백엔드

```bash
cd cert-app/backend

# uv 사용 시 (권장)
uv pip install -r requirements.txt
uv run uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

또는 기존 venv:

```bash
python -m venv venv
# Windows: venv\Scripts\activate
# macOS/Linux: source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

- API 베이스: **http://127.0.0.1:8000/api/v1**
- 헬스: **http://127.0.0.1:8000/health**

### 프론트엔드

```bash
cd cert-app/frontend/app
npm install
npm run dev
```

- 개발 서버: **http://localhost:5173** (또는 Vite 안내 주소)

### 환경 변수 (백엔드 `.env`)

```env
DATABASE_URL=postgresql://...
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_ANON_KEY=...
SUPABASE_SERVICE_ROLE_KEY=...
SUPABASE_JWT_SECRET=...
REDIS_URL=redis://...
OPENAI_API_KEY=sk-...

# 문의 폼 (선택)
SMTP_HOST=smtp.naver.com
SMTP_PORT=587
EMAIL_USER=your@naver.com
EMAIL_PASSWORD=<앱 비밀번호>
CONTACT_EMAIL=your@naver.com
```

프론트엔드 (Vite):

```env
VITE_API_BASE_URL=http://127.0.0.1:8000/api/v1
```

---

## 배포 요약

| 구분 | 서비스 | 비고 |
|------|--------|------|
| **Frontend** | Vercel | GitHub 연동 시 자동 배포, `VITE_API_BASE_URL` 설정 |
| **Backend** | Render | Root: `cert-app/backend`, Start: `uvicorn main:app --host 0.0.0.0 --port $PORT` |
| **DB** | Supabase | PostgreSQL + pgvector |
| **Cache** | Redis Cloud | `REDIS_URL` |

Render Free 플랜은 비활성 시 슬립 가능. `/health`로 UptimeRobot 등 모니터링 권장.

---

## AI 추천 품질 (임베딩 채우기)

자격증 테이블의 `embedding` 컬럼이 비어 있으면 시멘틱 검색이 동작하지 않습니다. 백엔드에서:

```bash
cd cert-app/backend
uv run python scripts/populate_certificates_vectors.py
```

- `OPENAI_API_KEY` 필요
- `--truncate`: 기존 벡터 비우고 재생성 (선택)

---

## 보안·Supabase

- **RLS**: `profiles`, `user_favorites`, `user_acquired_certs` 등 사용자 데이터는 RLS 정책으로 본인만 접근.
- **Leaked password protection**: Supabase Auth → Email provider에서 활성화 권장.
- **CORS**: 백엔드는 Bearer 토큰 인증 기준으로 `allow_origins=["*"]`, `allow_credentials=False` 사용.

---

## 라이선스

개인·포트폴리오 목적. 데이터는 참고용이며, 상업적 이용 시 해당 데이터 출처의 이용 약관을 확인하세요.

---

**CertFinder** — 데이터로 여는 당신의 미래.
