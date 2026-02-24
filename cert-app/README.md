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
- **Framework**: React 18, Vite (초고속 빌드 및 HMR)
- **Styling**: Tailwind CSS, Shadcn UI (Radix UI 기반 프리미엄 컴포넌트)
- **Animation**: Framer Motion
- **State Management**: Zustand, Custom Hooks (`useAuth`, `useRecommendations` 등)
- **API Client**: Fetch API + Custom Wrapper (Auto-retry & Mock Fallback)

### **Backend**
- **Framework**: FastAPI (Async 파이썬 웹 프레임워크)
- **Database**: PostgreSQL (Supabase 환경)
- **ORM**: SQLAlchemy, Alembic (마이그레이션)
- **Vector Search**: pgvector
- **Cache & Real-time**: 
  - **Redis** (`aioredis` 비동기 싱글톤 커넥션 풀)
  - `orjson` (초고속 JSON 처리)
- **Authentication**: Supabase Auth (OTP, 이메일/비밀번호)
- **External API**: OpenAI API (AI 추천)

---

## 프로젝트 구조 (Directory Structure)

```text
cert-app/
├── backend/                    # FastAPI 기반 백엔드 서비스
│   ├── app/
│   │   ├── api/                # API 라우터 (certs.py, fast_certs.py, auth.py, acquired_certs.py 등)
│   │   ├── core/               # 인증 패스워드 로직 (보안)
│   │   ├── models/             # SQLAlchemy 모델 (UserAcquiredCert 포함)
│   │   ├── schemas/            # Pydantic 타입 검증 모델
│   │   ├── services/           # 외부 연동(AI) 및 복잡한 비즈니스 로직
│   │   ├── utils/              # XP 계산 등 유틸 (xp.py: calculate_cert_xp, 레벨/티어)
│   │   └── redis_client.py     # 고성능 Redis 클라이언트
│   ├── main.py                 # FastAPI 진입점
│   ├── init.sql                # DB 스키마 (user_acquired_certs 테이블 포함)
│   └── requirements.txt        # 파이썬 의존성
├── frontend/                   # React.js 기반 프론트엔드 서비스
│   ├── app/src/
│   │   ├── components/         # 프리미엄 UI 컴포넌트
│   │   ├── hooks/              # 시스템 커스텀 훅 (ex: useAuth - 자동 세션 종료 포함)
│   │   ├── pages/              # MyPage(취득 자격증·티어·게이지바), CertDetail, Home 등
│   │   └── lib/                # API 클라이언트 (getAcquiredCerts, getAcquiredCertsSummary 등)
│   ├── package.json            # npm 의존성
│   └── vite.config.ts          # Vite 설정
└── docker-compose.yml          # 인프라 일괄 구동 스크립트
```

---

## 설치 및 실행 (Setup & Run)

### 1. 환경 변수 설정
```bash
# 백엔드 환경 설정
cp backend/.env.example backend/.env

# 프론트엔드 환경 설정
cp frontend/app/.env.example frontend/app/.env
```

### 2. 백엔드 실행
```bash
cd backend
python -m venv venv
# Windows: venv\Scripts\activate | Mac/Linux: source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload
```

### 3. 프론트엔드 실행
```bash
cd frontend/app
npm install
npm run dev
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
평균 난이도(5.0) 자격증 1개 ≈ 5 XP → Lv2 Bronze 도달.

---

## Redis 캐시 작동 원리

이 서비스는 가장 빠른 사용자 경험을 제공하기 위해 **자격증 조회**를 극단적으로 최적화했습니다.

1. **데이터 갱신 (Producer)**: 자격증 테이블에 CRUD가 발생할 경우 Redis Pub/Sub 채널(`cert_updates`)로 메시지 발행.
2. **실시간 싱크 (Sync Worker)**: 초경량 Python 워커가 채널을 구독하여 즉시 데이터를 orjson으로 직렬화해 Redis RAM 캐시에 꽂아넣습니다. (`app/redis_sync_worker.py`)
3. **가장 빠른 반환 (FastAPI Endpoint)**: 사용자가 앱에서 조회를 요청하면 백엔드(`app/api/fast_certs.py`)는 미들웨어나 모델 파싱조차 건너뛰고, Redis 비동기 풀(Pool)에서 원시 데이터를 꺼내 그대로 브라우저로 쏘아보냅니다.

---

## 이슈 트래킹 및 기여 (Troubleshooting & Contribution)
- 회원가입 인증 시 `check constraint "chk_userid_len"` 처럼 글자 수 제한이 걸리는 경우, Supabase Query를 통해 해당 제약조건을 Drop 처리하여 확장합니다.
- JWT 검증은 `app/utils/auth.py`에서 `python-jose` 대신, 직접 Supabase의 `/auth/v1/user` REST API에 검증을 위임하여 보안 호환성을 극대화 하였습니다.
