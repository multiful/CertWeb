# 🌐 CertFinder (자격증파인더)
### 대한민국 국가자격증 통합 분석 및 AI 경력 경로 추천 시스템

[![Deploy: Vercel](https://img.shields.io/badge/Deploy-Vercel-black?style=flat-square&logo=vercel)](https://cert-web-sand.vercel.app/)
[![Backend: FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688?style=flat-square&logo=fastapi)](https://fastapi.tiangolo.com/)
[![DB: PostgreSQL](https://img.shields.io/badge/DB-Supabase-3ECF8E?style=flat-square&logo=supabase)](https://supabase.com/)
[![Cache: Redis](https://img.shields.io/badge/Cache-Redis-DC382D?style=flat-square&logo=redis)](https://redis.io/)
[![Backend Deploy: Render](https://img.shields.io/badge/API-Render-46E3B7?style=flat-square&logo=render)](https://certweb-xzpx.onrender.com/health)

---

## 🚀 프로젝트 개요
**CertFinder**는 대한민국 **1,200여 종**의 국가 기술 및 전문 자격증 데이터를 실시간으로 분석하여 사용자에게 최적의 커리어 로드맵을 제시하는 지능형 플랫폼입니다. 단순 조회를 넘어 합격률 추이, 취업 전망, 전공 기반 AI 추천까지 데이터 기반의 자기계발을 완벽 지원합니다.

- **프론트엔드**: https://cert-web-sand.vercel.app
- **백엔드 API**: https://certweb-xzpx.onrender.com
- **API 상태 확인**: https://certweb-xzpx.onrender.com/health

---

## ✨ 핵심 기능 (Features)

### 1. 🔍 초고속 자격증 탐색 및 필터링
- **지능형 검색**: 1,200+ 국가기술·전문·민간 자격증을 키워드/분야/등급으로 즉각 필터링
- **정교한 데이터 분석**: 연도별/회차별 합격률, 난이도 점수, 응시자 추이 시각화 (Recharts)
- **북마크 기능**: 관심 자격증 즐겨찾기 저장 및 마이페이지 연동

### 2. 🤖 AI 기반 하이브리드 추천 엔진
- **전공 맞춤 추천**: 전공명 기반 퍼지 매칭(fuzzy matching)으로 최적의 자격증 자동 추천
- **AI 커리어 분석**: OpenAI GPT-4o 기반 사용자 맞춤형 커리어 리포트 생성
- **스마트 폴백(Fallback)**: "게임공학과" 등 비표준 전공명도 유사 매칭으로 정확히 추천

### 3. 👤 통합 계정 시스템
- **이메일 OTP 회원가입**: Supabase OTP 인증 기반 안전한 회원가입 플로우
- **Google OAuth 로그인**: 구글 계정 로그인 지원 (자동 userid 발급, 생년월일 선택 사항)
- **마이페이지**: 닉네임·전공·학년 수정, 즐겨찾기, 최근 조회, 맞춤 추천 대시보드
- **취득 자격증 (Acquired Certs)**: DB 자격증 목록에서 검색해 내가 취득한 자격증을 등록·관리
- **XP·레벨·티어 시스템**: 취득 자격증 난이도 기반 경험치(XP) 누적 → 9단계 레벨, Bronze/Silver/Gold/Platinum/Diamond 티어 + 레벨 게이지바 시각화
- **계정 삭제 연쇄 처리**: `ON DELETE CASCADE`로 탈퇴 시 모든 프로필 데이터 자동 삭제

### 4. 📬 문의하기 (Contact)
- Naver SMTP를 활용한 이메일 문의 접수 (백그라운드 처리로 API 응답 지연 없음)

### 5. ⚡ Ultra-low Latency 아키텍처
- **Redis Pipeline & Pub/Sub**: 서버 시작 시 핵심 데이터 메모리 선로딩, 캐시 히트율 최적화
- **orjson Serialization**: 표준 JSON 대비 고성능 직렬화
- **Cache-First 전략**: 모든 조회에 계층형 캐싱 적용
- **Rate Limiting**: 엔드포인트별 IP 기반 속도 제한으로 DDoS 방어

---

## 🛠 기술 스택 (Tech Stack)

| 영역 | 기술 |
|------|------|
| **Frontend** | React 18 + TypeScript, Vite, Tailwind CSS, shadcn/ui, Recharts |
| **Backend** | FastAPI (Python 3.11), SQLAlchemy 2.0, Pydantic v2, orjson |
| **Database** | PostgreSQL (Supabase), Redis Cloud |
| **Auth** | Supabase Auth (JWT), Google OAuth 2.0 |
| **Deployment** | Vercel (Frontend), Render (Backend) |
| **AI** | OpenAI GPT-4o |
| **Email** | Naver SMTP (smtplib) |

---

## 🗂 디렉토리 구조

```
CertWeb/
├── cert-app/
│   ├── backend/
│   │   ├── app/
│   │   │   ├── api/         # FastAPI 라우터 (certs, auth, recommendations, contact...)
│   │   │   ├── crud/        # DB CRUD 레이어
│   │   │   ├── models.py    # SQLAlchemy 모델
│   │   │   ├── schemas/     # Pydantic 스키마
│   │   │   └── services/    # Redis Sync, AI 서비스
│   │   ├── main.py          # FastAPI 앱 진입점
│   │   └── requirements.txt
│   └── frontend/
│       └── app/
│           ├── src/
│           │   ├── pages/   # MyPage, CertDetail, Home, ...
│           │   ├── components/
│           │   ├── hooks/   # useAuth, useRecommendations
│           │   └── lib/     # api.ts, supabase.ts
│           └── index.html
├── certs_no_pass_rate.csv   # 합격률 없는 자격증 보조 데이터
└── certs_with_pass_rate.csv # 합격률 포함 자격증 원본 데이터
```

---

## 📖 시작하기 (Getting Started)

### Prerequisites
- Python 3.11+
- Node.js 18+
- 가상환경 (권장: `python -m venv` 또는 `uv`)

### Backend Setup
```bash
cd cert-app/backend

# 가상환경 생성 및 활성화
python -m venv venv
venv\Scripts\activate      # Windows
# source venv/bin/activate  # macOS/Linux

pip install -r requirements.txt

# .env 파일 설정 후
uvicorn main:app --reload
```

**Cursor / VS Code에서 FastAPI(venv) 연결**
- **Ctrl+Shift+P** → **"Python: Select Interpreter"** 입력 후 선택
- 목록에서 `C:\Users\rlaeh\envs\fastapi\.venv\Scripts\python.exe` 선택 (또는 **Enter interpreter path**로 해당 경로 지정)
- 연결 후 해당 환경에서 디버깅·테스트·자동완성이 동작합니다.

**서버 실행**
```powershell
cd cert-app/backend
uv run python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
```
- 기본 주소: **http://127.0.0.1:8000** · API: **http://127.0.0.1:8000/api/v1** · 헬스: **http://127.0.0.1:8000/health**

### Frontend Setup
```bash
cd cert-app/frontend/app
npm install
npm run dev
```

### 환경변수 설정 (`.env`)
```env
DATABASE_URL=postgresql://...
SUPABASE_URL=https://...
SUPABASE_ANON_KEY=...
SUPABASE_SERVICE_ROLE_KEY=...
REDIS_URL=redis://...
EMAIL_USER=your@naver.com
EMAIL_PASSWORD=...
SMTP_HOST=smtp.naver.com
SMTP_PORT=465
OPENAI_API_KEY=sk-...
```

---

## 🔧 최근 주요 업데이트 (v1.2)

### 취득 자격증 & XP·레벨·티어 시스템
- ✅ **취득 자격증 (Acquired Certs)** — `user_acquired_certs` 테이블, `GET/POST/DELETE /me/acquired-certs` API, 마이페이지 모달에서 검색·추가·삭제
- ✅ **난이도 기반 XP 계산** — `app/utils/xp.py`: 9.0~9.9(+12), 8.0~8.9(+8), 7.0~7.9(+5), 6.0~6.9(+2), 5.0~5.9(0), 4.0~4.9(-0.5), 3.0~3.9(-1.0), 1.0~2.9(-0.5) → 최소 0.5 XP 보장
- ✅ **9단계 레벨·티어** — Lv1~2 Bronze, Lv3~4 Silver, Lv5~6 Gold, Lv7~8 Platinum, Lv9 Diamond (solved.ac 스타일 보석 색상)
- ✅ **레벨 임계값** — 평균 난이도(5.0) 자격증 1개(5 XP)로 Lv2 Bronze 도달 가능 (0→5→15→35→70→120→190→290→430 XP)
- ✅ **마이페이지 UI** — ACQUIRED CERTS 카드에 티어·레벨·XP 게이지바 표시; 우측 "내가 취득한 자격증" 섹션에 목록 + XP 뱃지; 백엔드 summary 미제공 시 프론트엔드 로컬 XP/티어 계산 폴백

### 이전 (v1.1)
- ✅ **Contact 이메일 라우터** 등록 및 Naver SMTP 연동 확인
- ✅ **ON DELETE CASCADE** 적용 — 계정 삭제 시 profiles 자동 연쇄 삭제
- ✅ **Google Auth** — 소셜 로그인 시 자동 userid 생성, 생년월일 선택 처리  
- ✅ **추천 Fallback** — "게임공학과" 등 비표준 전공명 퍼지 매칭으로 추천 오류 해결
- ✅ **MyPage loadData 경쟁조건 수정** — profile 비동기 로드 후 올바른 전공으로 추천 조회
- ✅ **닉네임 변경 즉시 반영** — 저장 후 `supabase.auth.refreshSession()` 호출로 상단 메뉴 동기화
- ✅ **Saved Certs 카드 복원** — 마이페이지 상단 요약에 북마크 수 표시 재추가

---

## 🔒 Supabase 보안 경고 대응

대시보드 **Project Settings → Reports → Issues** 에서 다음처럼 처리할 수 있습니다.

| 경고 | 조치 |
|------|------|
| **Function Search Path Mutable** | 함수 정의 시 `SET search_path = public` 추가. `update_modified_column` 은 `vector_migration.sql` 참고. |
| **Extension in Public** | (선택) pgvector를 `extensions` 스키마로 이동 (Supabase/PostgreSQL 문서 참고). |
| **Leaked Password Protection Disabled** | **Authentication → Providers → Email** 에서 **Enable leaked password protection** 활성화 (유출 비밀번호 목록 대조). |
| **RLS Disabled in Public** | **SQL Editor**에서 public 테이블에 RLS 활성화 및 정책 추가 (참조 테이블 읽기 전용, profiles/즐겨찾기/취득자격 본인만 CRUD). |

### RAG 검색 품질 (certificates_vectors 채우기)
자격증 DB 기준으로 RAG 벡터를 채우면 `/certs/search/rag` 검색 품질이 좋아집니다.  
`cert-app/backend`에서:
```bash
uv run python scripts/populate_certificates_vectors.py
```
- 기존 동일 `qual_id` 행은 갱신, 새 자격만 추가됩니다.  
- 처음부터 비우고 채우려면: `--truncate`  
- OpenAI API 호출이 필요하므로 `OPENAI_API_KEY` 설정 필요.

---

## 📄 License
This project is for personal portfolio purposes. All data is provided for informational use only.

---

**CertFinder** - 데이터로 여는 당신의 미래.
