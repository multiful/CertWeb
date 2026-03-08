# 🚀 CertFinder Backend
### 고성능 비동기 자격증 분석 API 서버

---

## 🏗 프로젝트 구조 (Project Structure)

```text
backend/
├── app/
│   ├── api/            # API 엔드 포인트 핸들러
│   │   ├── auth.py     # 사용자 인증 및 프로필 관리
│   │   ├── certs.py    # 자격증 조회 및 검색 (Standard)
│   │   ├── fast_certs.py # Redis 기반 초고속 자격증 조회
│   │   ├── jobs.py      # 직무 정보 조회
│   │   └── recommendations.py # AI 및 전공 기반 추천
│   ├── services/       # 비즈니스 로직 및 외부 연동
│   │   ├── fast_sync_service.py # Redis Pipelining 벌크 동기화
│   │   ├── law_update_pipeline.py # 법령 정보 및 벡터 DB 파이프라인
│   │   └── vector_service.py # OpenAI Embedding 연동
│   ├── utils/          # 공통 유틸리티
│   │   ├── auth.py     # JWT 인증 유틸
│   │   └── stream_producer.py # Redis Pub/Sub 이벤트 발행
│   ├── redis_client.py # orjson 기반 고성능 Redis 클라이언트
│   ├── database.py     # SQLAlchemy 엔진 및 세션 관리
│   ├── models.py       # SQLAlchemy ORM 모델
│   └── schemas/        # Pydantic 데이터 검증 모델
├── main.py             # FastAPI 메인 실행 파일 및 Lifespan 관리
├── requirements.txt    # 의존성 패키지 목록
└── .env.example        # 환경 변수 템플릿
```

---

## ⚡ 주요 기술적 특징

1.  **Ultra-fast Serialization**: `orjson`을 전면 도입하여 대용량 자격증 리스트 반환 시 JSON 직렬화 병목을 제거했습니다.
2.  **Redis-First Architecture**: 단순 캐싱을 넘어 `FastSyncService`를 통해 부팅 시 전체 인덱스를 Redis로 로드하여 하드웨어 성능을 극한으로 끌어올립니다.
3.  **Real-time Cache Sync**: `StreamProducer`를 이용한 Redis Pub/Sub 기반의 실시간 캐시 갱신 모델을 구현했습니다.
4.  **AI Hybrid Engine**: 벡터 검색(Semantic Search)과 전통적인 필터링을 결합한 하이브리드 추천 엔진을 제공합니다.

---

reranker : Dongjin-kr/ko-reranker

## Dense/Vector 검증 및 운영 기본값

- **표준 평가 골든셋**: `data/reco_golden_recommendation_18.jsonl` (18질의). 평가는 이 파일 기준으로 수행한다.
- **Ablation**: `uv run python scripts/run_dense_ablation.py --golden data/reco_golden_recommendation_18.jsonl [--max-queries N] [--output-csv path]`
- **Rewrite 품질**: `rewrite_for_dense` 출력은 평가 스크립트(`eval_contrastive_profile_once.py` 등) 실행 시 재질의가 반영된 retrieval로 간접 확인.
- **Contrastive 데이터 검증**: `uv run python scripts/validate_contrastive_dataset.py --samples data/contrastive_train.jsonl [--triplets data/contrastive_triplets.jsonl] [--report path]`
- 상세: [docs/DENSE_VECTOR_OPERATIONAL_DEFAULTS.md](docs/DENSE_VECTOR_OPERATIONAL_DEFAULTS.md)

## 🛠 실행 방법 (Installation)

1.  `.env` 파일 설정 (참고: `.env.example`)
2.  의존성 설치: `pip install -r requirements.txt`
3.  서버 실행: `uvicorn main:app --reload`
