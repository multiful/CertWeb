## 프로젝트 구조

cert-app/
├── backend/
│   ├── app/
│   │   ├── api/                # API 엔드포인트 계층
│   │   │   ├── v1/             # API 버전 관리
│   │   │   │   ├── api.py      # 모든 라우터 통합
│   │   │   │   └── endpoints/  # 기능별 라우트 분리
│   │   │   │       ├── certs.py
│   │   │   │       ├── recommendations.py
│   │   │   │       ├── admin.py
│   │   │   │       └── favorites.py
│   │   ├── core/               # 앱 공통 설정
│   │   │   ├── config.py       # Pydantic Settings 환경 변수 관리
│   │   │   ├── security.py     # 인증 및 보안 설정
│   │   │   └── redis.py        # Redis 클라이언트 초기화
│   │   ├── db/                 # 데이터베이스 계층
│   │   │   ├── base.py         # 모든 모델 통합 (Alembic용)
│   │   │   └── session.py      # 엔진 및 세션 설정
│   │   ├── models/             # SQLAlchemy 모델 (도메인별 분리)
│   │   │   ├── cert.py
│   │   │   ├── user.py
│   │   │   └── stats.py
│   │   ├── schemas/            # Pydantic 스키마 (Request/Response 모델)
│   │   │   ├── cert.py
│   │   │   ├── recommendation.py
│   │   │   └── common.py       # 공통 응답 규격
│   │   ├── crud/               # DB 직접 접근 로직 (도메인별 분리)
│   │   │   ├── crud_cert.py
│   │   │   └── crud_user.py
│   │   └── services/           # 비즈니스 로직 (복합 로직 처리)
│   │       └── recommend_service.py
│   ├── main.py                 # 앱 초기화 및 미들웨어 설정
│   ├── alembic/                # DB 마이그레이션 관리 (권장)
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── api/                # Axios 클라이언트 및 API 호출 함수
│   │   ├── components/         # 재사용 가능한 공통 UI
│   │   │   ├── common/         # Button, Modal 등
│   │   │   └── layout/         # Header, Footer
│   │   ├── features/           # 도메인 중심 기능 구조 (권장)
│   │   │   ├── certs/          # 자격증 관련 컴포넌트 & 로직
│   │   │   └── recommendations/# 추천 관련 컴포넌트 & 로직
│   │   ├── hooks/              # 커스텀 훅 (useAuth, useCerts 등)
│   │   ├── lib/                # 유틸리티 (utils, formatters)
│   │   ├── pages/              # 라우트별 페이지 컴포넌트
│   │   ├── store/              # 전역 상태 관리 (Zustand 등)
│   │   └── types/              # TypeScript 인터페이스
│   ├── public/
│   ├── Dockerfile
│   └── package.json
├── docker-compose.yml
└── README.md


1. 환경 변수 설정
각 디렉토리의 .env.example 파일을 복사하여 실제 환경에 맞는 설정값을 입력합니다.

```bash
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env
```

2. Docker를 이용한 실행


```bash
# 전체 서비스 실행 (Frontend, Backend, DB, Redis)
docker-compose up -d

# n8n 자동화 도구를 포함하여 실행할 경우
docker-compose --profile n8n up -d
```


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