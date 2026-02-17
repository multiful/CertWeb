# CertFinder - 자격증 검색 및 추천 서비스

Flutter 앱으로 개발되었던 자격증 조회/추천 앱을 웹 서비스로 전환한 프로젝트입니다.

## 기술 스택

### Backend
- **FastAPI** - Python 기반 고성능 웹 프레임워크
- **SQLAlchemy** - ORM for PostgreSQL
- **Pydantic** - 데이터 검증 및 직렬화
- **PostgreSQL** - 메인 데이터베이스 (Supabase 호환)
- **Redis** - 캐싱 및 레이트 리미팅

### Frontend
- **React + TypeScript** - UI 프레임워크
- **Vite** - 빌드 도구
- **Tailwind CSS** - 스타일링
- **shadcn/ui** - UI 컴포넌트
- **React Router** - 클라이언트 사이드 라우팅
- **Recharts** - 차트 라이브러리

### Infrastructure
- **Docker Compose** - 로컬 개발 환경
- **n8n** - 자동화 워크플로우 (선택)

## 프로젝트 구조

```
cert-app/
├── backend/              # FastAPI 백엔드
│   ├── app/
│   │   ├── api/         # API 라우트
│   │   │   ├── certs.py
│   │   │   ├── recommendations.py
│   │   │   ├── admin.py
│   │   │   └── favorites.py
│   │   ├── config.py    # 설정
│   │   ├── crud.py      # CRUD 작업
│   │   ├── database.py  # DB 연결
│   │   ├── models.py    # SQLAlchemy 모델
│   │   ├── redis_client.py  # Redis 클라이언트
│   │   └── schemas.py   # Pydantic 스키마
│   ├── main.py          # FastAPI 앱
│   ├── Dockerfile
│   ├── requirements.txt
│   └── init.sql         # 초기 데이터
├── frontend/            # React 프론트엔드
│   ├── src/
│   │   ├── components/  # UI 컴포넌트
│   │   ├── hooks/       # 커스텀 훅
│   │   ├── lib/         # 유틸리티
│   │   ├── pages/       # 페이지 컴포넌트
│   │   └── types/       # TypeScript 타입
│   ├── Dockerfile
│   └── package.json
├── docker-compose.yml
└── README.md
```

## 주요 기능

### 1. 자격증 검색 (/certs)
- 이름 검색
- 분야, NCS 대직무, 종류, 시행기관 필터링
- 정렬 (이름, 합격률, 난이도, 최신순)
- 페이지네이션
- URL 쿼리 스트링 동기화

### 2. 자격증 상세 (/certs/:id)
- 기본 정보 (이름, 종류, 분야, 시행기관 등)
- 연도별 통계 테이블
- 합격률 추이 차트
- 난이도, 응시자 수 통계

### 3. 추천 서비스 (/recommendations)
- 전공 기반 자격증 추천
- 추천 점수 및 이유 제공
- 합격률 정보 포함

### 4. 캐싱 전략
- `/certs` - 5분 TTL
- `/certs/:id` - 30분 TTL
- `/certs/:id/stats` - 1시간 TTL
- `/recommendations` - 10분 TTL

### 5. 레이트 리미팅
- IP 기준 100요청/60초
- Redis 기반 구현

## 로컬 실행

### 사전 요구사항
- Docker & Docker Compose
- (선택) Node.js 20+ (프론트엔드 개발 시)
- (선택) Python 3.11+ (백엔드 개발 시)

### Docker Compose로 실행

```bash
# 프로젝트 클론
cd cert-app

# 환경 변수 설정
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env

# 전체 스택 실행
docker-compose up -d

# 또는 n8n 포함 실행
docker-compose --profile n8n up -d
```

서비스 접속:
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs
- n8n (선택): http://localhost:5678

### 개발 모드 실행

**백엔드:**
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# 환경 변수 설정
cp .env.example .env
# .env 파일 편집

# 실행
uvicorn main:app --reload
```

**프론트엔드:**
```bash
cd frontend
npm install

# 환경 변수 설정
cp .env.example .env
# .env 파일 편집

# 실행
npm run dev
```

## API 엔드포인트

### 자격증 API
- `GET /api/v1/certs` - 자격증 목록 (검색/필터/정렬/페이지네이션)
- `GET /api/v1/certs/filter-options` - 필터 옵션
- `GET /api/v1/certs/:id` - 자격증 상세
- `GET /api/v1/certs/:id/stats` - 통계 목록

### 추천 API
- `GET /api/v1/recommendations?major=...` - 전공 기반 추천
- `GET /api/v1/recommendations/majors` - 전공 목록

### 관리자 API (X-Job-Secret 필요)
- `POST /api/v1/admin/cache/invalidate` - 캐시 무효화
- `POST /api/v1/admin/cache/flush` - 전체 캐시 삭제
- `POST /api/v1/admin/sync/stats` - 통계 동기화
- `POST /api/v1/admin/rebuild/recommendations` - 추천 재계산

### 즐겨찾기 API (인증 필요)
- `GET /api/v1/me/favorites` - 즐겨찾기 목록
- `POST /api/v1/me/favorites/:id` - 즐겨찾기 추가
- `DELETE /api/v1/me/favorites/:id` - 즐겨찾기 삭제

### 헬스체크
- `GET /health` - 서비스 상태 확인

## 환경 변수

### Backend (.env)
```env
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/certdb
REDIS_URL=redis://localhost:6379/0
JOB_SECRET=your-super-secret-key
DEBUG=false
CACHE_TTL_LIST=300
CACHE_TTL_DETAIL=1800
CACHE_TTL_STATS=3600
CACHE_TTL_RECOMMENDATIONS=600
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_WINDOW=60
```

### Frontend (.env)
```env
VITE_API_BASE_URL=http://localhost:8000/api/v1
```

## n8n 자동화

n8n을 사용한 자동화 워크플로우 예시:

### 1. 데이터 수집 자동화
```
Schedule Trigger (매일 00:00)
  → HTTP Request (외부 API 호출)
  → Function (데이터 변환)
  → HTTP Request (POST /admin/sync/stats)
```

### 2. 캐시 리프레시
```
Schedule Trigger (매시간)
  → HTTP Request (POST /admin/cache/invalidate)
    Header: X-Job-Secret: your-secret
```

### 3. 추천 재계산
```
Schedule Trigger (매주 월요일)
  → HTTP Request (POST /admin/rebuild/recommendations)
    Header: X-Job-Secret: your-secret
```

## 데이터베이스 스키마

### qualification (자격증)
- qual_id (PK)
- qual_name
- qual_type
- main_field
- ncs_large
- managing_body
- grade_code
- is_active

### qualification_stats (통계)
- stat_id (PK)
- qual_id (FK)
- year, exam_round
- candidate_cnt, pass_cnt
- pass_rate, difficulty_score

### major_qualification_map (추천 매핑)
- map_id (PK)
- major, qual_id (FK)
- score, weight, reason

## 라이선스

MIT License
