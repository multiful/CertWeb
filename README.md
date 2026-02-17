# CertFinder - 자격증 검색 및 추천 서비스

[개인프로젝트]

자격증 조회/추천 앱을 웹 서비스로 전환한 개인 프로젝트입니다.


배포 : https://cert-h0z1gkfz9-multifuls-projects.vercel.app/
노션 : https://puzzling-patio-678.notion.site/2f246c0be18b8005822dc62d03bff584#2f246c0be18b80e7abdcf6c93bb2e308



---------------------------------------------------------------------------------



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
