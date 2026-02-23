# Cert-App (프로젝트명: 안티그래비티)

**"무중력 속도(Ultra-low Latency)로 경험하는 맞춤형 자격증 추천 플랫폼"**

안티그래비티(Anti-gravity) 프로젝트는 방대한 자격증 데이터를 가장 빠르고 정확하게 탐색하고, 사용자 전공 및 선호도에 맞춰 지능적으로 추천해주는 웹 서비스입니다. 

---

## 주요 기능 (Features)

1. **초저지연(Ultra-low Latency) 자격증 조회 시스템**
   - **Quix Streams + Redis 비동기 캐싱**: DB 조회 없이 1ms 내의 응답 제공
   - **orjson 직렬화**: FastAPI 엔드포인트에서 JSON 직렬화 오버헤드 극대화 억제
2. **AI 기반 자격증 맞춤 추천 (Vector DB)**
   - **pgvector & Supabase**: 자격증 요약 텍스트 임베딩을 이용한 시맨틱 유사도 검색
   - **OpenAI API**: 사용자 전공과 관심사를 분석하여 가장 적합한 트랙 제안
3. **인증 및 보안 (Auth & Security)**
   - **Supabase Auth**: 안전한 JWT 기반 세션 관리 (자체 DB 연동 백업)
   - 소셜 로그인 연동 (Google 등) 기능 
4. **모던 UI/UX (Frontend)**
   - 최신 **React + Vite** 아키텍처 사용
   - **TailwindCSS + Shadcn UI** 조합으로 빠르고 직관적인 사용자 경험 제공
5. **데이터 파이프라인 자동화 (n8n)**
   - 백그라운드에서 공공 API 및 통계 데이터를 주기적으로 동기화 
   - 캐시 리프레시 및 통계 자동 업데이트 수행

---

## 기술 스택 (Tech Stack)

### **Frontend**
- **Framework**: React 18, Vite
- **Styling**: Tailwind CSS, Shadcn UI, Framer Motion (애니메이션)
- **State Management**: Zustand, Custom Hooks (`useAuth`, `useRecommendations` 등)
- **API Client**: Fetch / Axios 래퍼

### **Backend**
- **Framework**: FastAPI (Async 파이썬 웹 프레임워크)
- **Database**: PostgreSQL (Supabase 환경)
- **ORM**: SQLAlchemy, Alembic (마이그레이션)
- **Vector Search**: pgvector
- **Cache & Real-time**: 
  - **Redis** (`aioredis` 비동기 싱글톤 커넥션 풀)
  - **Quix Streams** (실시간 데이터 동기화 파이프라인)
  - `orjson` (초고속 JSON 처리)
- **Authentication**: Supabase Auth (OTP, 이메일/비밀번호)
- **External API**: OpenAI API (AI 추천)

### **Infrastructure & Automation**
- **Docker**: `docker-compose.yml`을 통한 멀티 컨테이너 환경 구성 
- **Workflow**: n8n 스케줄링 (통계 파이프라인 구축)

---

## 프로젝트 구조 (Directory Structure)

```text
cert-app/
├── backend/                    # FastAPI 기반 백엔드 서비스
│   ├── app/
│   │   ├── api/                # API 라우터 (certs.py, fast_certs.py, auth.py 등)
│   │   ├── core/               # 인증 패스워드 로직 (보안)
│   │   ├── db/                 # RDB 세션 및 엔진 세팅
│   │   ├── models/             # SQLAlchemy 모델 (qualifications, profiles 등)
│   │   ├── schemas/            # Pydantic 타입 검증 모델
│   │   ├── crud/               # 데이터베이스 쿼리 함수 모음
│   │   ├── services/           # 외부 연동(AI) 및 복잡한 비즈니스 로직
│   │   ├── quix_worker.py      # Quix Streams 실시간 동기화 워커
│   │   └── redis_client.py     # 싱크 및 어싱크 Redis 클라이언트 풀
│   ├── alembic/                # DB 마이그레이션 관리
│   ├── main.py                 # FastAPI 진입점 (Lifespan 이벤트)
│   └── requirements.txt        # 파이썬 의존성
├── frontend/                   # React.js 기반 프론트엔드 서비스
│   ├── app/src/
│   │   ├── api/                # 백엔드 연동 클라이언트 설정
│   │   ├── components/         # 통합 UI 컴포넌트 목록
│   │   ├── hooks/              # 시스템 커스텀 훅 (ex: useAuth)
│   │   ├── pages/              # 렌더링용 페이지 뷰
│   │   └── lib/                # API, Utils 함수 및 라우터 정의
│   ├── public/                 # 에셋 파일
│   └── package.json            # npm 의존성 정의 파일
└── docker-compose.yml          # 인프라 일괄 구동 스크립트 (n8n 등)
```

---

## 설치 및 실행 (Setup & Run)

### 1. 환경 변수 설정
```bash
# 백엔드 환경 설정 (Supabase url, OpenAI api key 등)
cp backend/.env.example backend/.env

# 프론트엔드 환경 설정 (VITE_API_BASE_URL 등)
cp frontend/app/.env.example frontend/app/.env
```

### 2. 백엔드 실행 (로컬 개발 모드)
> **Python 3.10 이상 권장**
```bash
cd backend

# 가상환경 세팅 및 활성화 (개발자에 따라 uv 또는 venv 사용)
python -m venv venv
source venv/Scripts/activate

# 의존성 설치 (quixstreams, orjson, fastapi_redis 등)
pip install -r requirements.txt

# FastAPI 서버 시작
uvicorn main:app --reload

# Quix Streams 데이터 동기화 워커 실행 (배포 시 별도 프로세스)
python app/quix_worker.py
```

### 3. 프론트엔드 실행
```bash
cd frontend/app
npm install

npm run dev
```

### 4. Docker Compose
전체 서비스를 격리된 환경에서 실행하려면(또는 n8n 포함 시):
```bash
docker-compose up -d

# 통계 수집 자동화 스케줄러 n8n 활성화 시
docker-compose --profile n8n up -d
```

---

## Quix Streams + Redis 작동 원리

이 서비스는 가장 빠른 사용자 경험을 제공하기 위해 **자격증 조회**를 극단적으로 최적화했습니다.

1. **데이터 갱신 (Producer)**: 자격증 테이블에 CRUD가 발생할 경우 Kafka 토픽 혹은 이벤트 스트림 발생.
2. **실시간 싱크 (Quix Streams Worker)**: 초경량 Python 워커가 토픽을 구독(`Consumer`)하여 즉시 데이터를 orjson으로 직렬화해 Redis RAM 캐시에 꽂아넣습니다. (`app/quix_worker.py`)
3. **가장 빠른 반환 (FastAPI Endpoint)**: 사용자가 앱에서 조회를 요청하면 백엔드(`app/api/fast_certs.py`)는 미들웨어나 모델 파싱조차 건너뛰고, `aioredis` 비동기 풀(Pool)에서 원시 바이트스트림 데이터를 꺼내 그대로 브라우저로 쏘아보냅니다.

---

## 이슈 트래킹 및 기여 (Troubleshooting & Contribution)
- 회원가입 인증 시 `check constraint "chk_userid_len"` 처럼 글자 수 제한이 걸리는 경우, Supabase Query를 통해 해당 제약조건을 Drop 처리하여 확장합니다.
- JWT 검증은 `app/utils/auth.py`에서 `python-jose` 대신, 직접 Supabase의 `/auth/v1/user` REST API에 검증을 위임하여 보안 호환성을 극대화 하였습니다.
