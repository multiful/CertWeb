# 🌐 CertFinder (자격증파인더)
### 대한민국 국가자격증 통합 분석 및 AI 경력 경로 추천 시스템

[![Deploy: Vercel](https://img.shields.io/badge/Deploy-Vercel-black?style=flat-square&logo=vercel)](https://cert-h0z1gkfz9-multifuls-projects.vercel.app/)
[![Backend: FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688?style=flat-square&logo=fastapi)](https://fastapi.tiangolo.com/)
[![DB: PostgreSQL](https://img.shields.io/badge/DB-PostgreSQL-336791?style=flat-square&logo=postgresql)](https://www.postgresql.org/)
[![Storage: Redis](https://img.shields.io/badge/Cache-Redis-DC382D?style=flat-square&logo=redis)](https://redis.io/)

---

## 🚀 프로젝트 개요
**CertFinder**는 대한민국 **1,000여 종**의 국가 기술 및 전문 자격증 데이터를 실시간으로 분석하여 사용자에게 최적의 커리어 로드맵을 제시하는 지능형 플랫폼입니다. 단순 조회를 넘어 합격률 추이, 취업 전망, 그리고 AI 기반의 직무 매칭 서비스를 통해 데이터 기반의 자기계발을 지원합니다.

---

## ✨ 핵심 기능 (Features)

### 1. 초고속 자격증 탐색 및 필터링
*   **지능형 검색**: 600+ 기술/전문 자격증 데이트를 즉각적으로 필터링.
*   **정교한 데이터 분석**: 연도별/회차별 합격률, 난이도 변화, 응시자 추이 시각화.
*   **다이나믹 대시보드**: Recharts를 활용한 직관적인 통계 분석 리포트.

### 2. AI 기반 하이브리드 추천 엔진
*   **전공 맞춤 매핑**: 사용자의 전공과 실제 취업 시장 데이터를 매칭하여 최적의 자격증 추천.
*   **AI 커리어 분석**: OpenAI GPT-4 기반으로 사용자의 관심사와 자격증 간의 연계성 분석.
*   **실시간 트렌딩**: 현재 가장 인기 있는 자격증 및 유망 자격증 실시간 순위 제공.

### 3. 초저지연(Ultra-low Latency) 아키텍처
*   **Redis Pipeline & Pub/Sub**: 실시간 데이터 동기화 및 대규모 벌크 작업 최적화.
*   **orjson Serialization**: 표준 JSON 대비 10배 이상의 속도를 자랑하는 고성능 직렬화 엔진 도입.
*   **Cache-First 전략**: 모든 조회 요청에 대해 계층형 캐싱 알고리즘 적용.

---

## 🛠 기술 스택 (Tech Stack)

### Backend (Python Core)
*   **FastAPI**: 비동기 처리를 통한 초고속 API 서버 구축.
*   **SQLAlchemy (PostgreSQL)**: 관계형 데이터베이스 모델링 및 정교한 통계 쿼리.
*   **Redis Pub/Sub**: 서버 간 실시간 이벤트 브로드캐스팅 및 실시간 캐시 동기화.
*   **orjson & Pydantic V2**: 데이터 검증 및 직렬화 성능 극대화.

### Frontend (Modern UX)
*   **React + TypeScript**: 안정적이고 유지보수가 용이한 프론트엔드 아키텍처.
*   **Vite**: 초고속 개발 환경 및 최적화된 빌드 프로세스.
*   **Tailwind CSS & shadcn/ui**: 커스텀 디자인 시스템 기반의 프리미엄 UI/UX.
### 3. 보안 및 세션 관리
*   **Supabase Auth 기반 보안**: JWT를 활용한 안전한 인증 체계 구축.
*   **Professional Session Timeout**: 보안 강화를 위해 1시간 동안 활동이 없을 경우 자동으로 로그아웃되는 지능형 세션 관리 시스템 구현.

---

## 🏗 시스템 아키텍처 (Architecture Highlights)

### ⚡ 하이 퍼포먼스 데이터 파이프라인
CertFinder는 유료 인프라 비용을 제로화하면서도 기업급 성능을 유지하기 위해 다음과 같은 아키텍처를 채택했습니다:

1.  **FastSync Service**: 서버 구동 시 DB의 핵심 데이터를 Redis Pipelining을 통해 수 초 내에 메모리로 로드합니다.
2.  **Redis Pub/Sub Sync**: 데이터 변경 시 Kafka와 같은 무거운 브로커 없이도 실시간으로 모든 캐시 노드에 이벤트를 전파합니다.
3.  **Hybrid Recommendation**: 정적 전공 매핑(SQL)과 동적 관심사 분석(AI)을 결합한 하이브리드 알고리즘을 사용합니다.

---

## 📖 시작하기 (Getting Started)

### Prerequisites
- Python 3.10+
- Node.js 18+
- Docker & Docker Compose (for local development)

### Backend Setup
```bash
cd cert-app/backend
python -m venv venv
source venv/bin/activate  # Windows: venv\\Scripts\\activate
pip install -r requirements.txt
uvicorn main:app --reload
```

### Frontend Setup
```bash
cd cert-app/frontend/app
npm install
npm run dev
```

---

## 📄 License
This project is for personal portfolio purposes. All data is provided for informational use only.

---

**CertFinder** - 데이터로 여는 당신의 미래.
