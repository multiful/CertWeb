# CertFinder (자격증파인더)

**대한민국 국가자격증 통합 분석 및 AI 경력 경로 추천 시스템**

[![Deploy: Vercel](https://img.shields.io/badge/Deploy-Vercel-black?style=flat-square&logo=vercel)](https://vercel.com/)
[![Backend: FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688?style=flat-square&logo=fastapi)](https://fastapi.tiangolo.com/)
[![DB: Supabase](https://img.shields.io/badge/DB-Supabase-3ECF8E?style=flat-square&logo=supabase)](https://supabase.com/)
[![Cache: Redis](https://img.shields.io/badge/Cache-Redis-DC382D?style=flat-square&logo=redis)](https://redis.io/)
[![API: Railway](https://img.shields.io/badge/API-Railway-0B0D0E?style=flat-square&logo=railway)](https://certfinder-production.up.railway.app/health)

---

## 프로젝트 개요

**CertFinder**는 대한민국 **1,101개** 국가 기술·전문 자격증 데이터를 실시간으로 분석해, 사용자에게 맞는 자격증과 직무 정보를 제공하는 웹 플랫폼입니다. 합격률·난이도·취업 전망과 함께 **전공 기반 AI 추천**, **직무 분석**, **북마크·취득 자격증 관리**까지 한 곳에서 이용할 수 있습니다.

| 환경 | URL |
|------|-----|
| **프론트엔드** | https://cert-web-sand.vercel.app |
| **백엔드 API** | https://certfinder-production.up.railway.app *(도메인은 변경될 수 있음)* |
| **헬스 체크** | https://certfinder-production.up.railway.app/health |

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
- **알고리즘**: 전공 매핑 + 하이브리드 검색(벡터 + 풀텍스트, RRF) → 합격률·난이도 보정 → 규칙 기반 맞춤 이유 생성
- **퍼지 전공 매칭**: DB에 없는 전공명은 pg_trgm 유사도로 근접 전공 사용
- **취득 자격증 제외**: 로그인 시 이미 취득한 자격증은 추천 후보에서 제외
- **게스트**: 비로그인 시 결과 3개 제한; 로그인 시 **최대 15개** 결과 제공

### 4. 계정·마이페이지

- **인증**: Supabase Auth (이메일 OTP, Google OAuth)
- **마이페이지**: 닉네임·전공·학년, 북마크·취득 자격증, XP·레벨·티어. 탭 전환 후 복귀 시 90초 캐시로 즉시 표시 후 백그라운드 갱신
- **취득 자격증**: DB 자격증 검색 후 등록·삭제, XP 누적
- **문의하기**: Naver SMTP 이메일 발송 (백엔드 비동기 처리)

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
| **AI** | OpenAI text-embedding-3-small (검색·추천), 선택적 GPT 계열 모델(법령 요약·벡터 인덱싱 파이프라인) |
| **배포** | Vercel (Frontend), Railway (Backend, 임시 도메인 가능) |
| **이메일** | Naver SMTP (문의 폼) |

---

## 디렉토리 구조

```
CertWeb/
├── cert-app/
│   ├── backend/                    # FastAPI
│   │   ├── app/
│   │   │   ├── api/                # 라우터 (certs, jobs, recommendations, ai_recommendations, contact, me, ...)
│   │   │   ├── crud.py, models.py
│   │   │   ├── schemas/
│   │   │   ├── utils/               # ai.py (embedding, query expansion, LLM rerank/reason)
│   │   │   └── services/
│   │   ├── main.py
│   │   ├── requirements.txt
│   │   └── scripts/                # 평가(eval_three_models_no_reranker), 적용 검증(bench_apply_verification) 등
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

## 운영/유지보수 메모 (내부용)

이 서비스는 **Vercel(프론트) + Railway(백엔드) + Supabase(Postgres) + Redis Cloud** 환경에 배포된 상태로 운영되며,  
일반 사용자가 로컬에서 직접 서버를 띄우는 것을 전제로 하지 않습니다. 아래 내용은 **운영자용 메모**입니다.

- **환경 변수 분리**
  - 프론트(Vercel): `VITE_API_BASE_URL`, `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY` 등 브라우저에서 필요한 값만 저장.
  - 백엔드(Railway 등): `DATABASE_URL`, `REDIS_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_JWT_SECRET`, `OPENAI_API_KEY` 등 비밀 키는 모두 호스트 환경변수에만 저장.
  - DB 접속 정보나 Service Role Key, JWT Secret은 Vercel에 두지 않고 노출 시 즉시 키를 회전(재발급)한다.

- **RAG 임베딩 관리**
  - 자격증 요약 텍스트 임베딩은 Supabase `certificates_vectors` 테이블에 미리 저장되어 있으며,
    필요 시 운영자가 RAG 인덱스 빌드 스크립트를 안전한 환경(로컬 관리자 또는 백엔드 워커)에서 실행해 재생성한다.
  - 이 작업에는 `OPENAI_API_KEY`와 DB 권한이 필요하므로, 일반 사용자는 수행할 수 없다.

- **모니터링**
  - 백엔드 `/health` 엔드포인트와 UptimeRobot 등으로 다운 여부를 모니터링한다.
  - `ai_recommendations` 모듈에서 남기는 metrics 로그(응답 시간, 후보 수, 점수 분포)를 통해 AI 추천 품질·속도를 정기적으로 점검한다.

로컬 개발/실행 방법은 문서에서 제거하고, 배포된 웹 서비스를 기준으로만 안내한다.

---

## 배포 요약

| 구분 | 서비스 | 비고 |
|------|--------|------|
| **Frontend** | Vercel | GitHub 연동 시 자동 배포, `VITE_API_BASE_URL` (Railway API URL + `/api/v1`) |
| **Backend** | Railway | Root: `cert-app/backend`, Start: `uvicorn main:app --host 0.0.0.0 --port $PORT` |
| **DB** | Supabase | PostgreSQL + pgvector |
| **Cache** | Redis Cloud | `REDIS_URL` |

Railway/호스트별로 슬립 정책이 다를 수 있음. `/health`로 UptimeRobot 등 모니터링 권장.

---

## AI 추천 품질 (개발자 참고)

- AI 추천은 Supabase `certificates_vectors` 테이블의 임베딩과 통계 테이블(`qualification_stats`)을 기반으로 동작한다.
- 운영 중에는 주기적으로 데이터 변경 여부를 확인하고, 필요 시 운영자가 RAG 인덱스를 재생성한다.
- 이 과정은 배포된 서비스의 일환으로만 수행되며, 일반 사용자는 임베딩 생성/갱신 작업에 접근할 수 없다.

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
