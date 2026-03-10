# CertFinder Backend

**CertFinder** 자격증 검색·추천 API 백엔드. 고성능 비동기 서버로, **Hybrid RAG**(BM25 + Vector + Contrastive 3-way RRF + Reranker) 기반 검색·추천과 Redis 기반 초고속 조회를 제공합니다.

---

## 목차

- [프로젝트 구조](#-프로젝트-구조)
- [주요 기술 스택](#-주요-기술-스택)
- [RAG 파이프라인 개요](#-rag-파이프라인-개요)
- [RAG 고도화 방식 및 성과](#-rag-고도화-방식-및-성과)
- [실행 방법](#-실행-방법)
- [평가 및 골든셋](#-평가-및-골든셋)
- [데이터·스크립트](#-데이터스크립트)
- [참고 문서](#-참고-문서)

---

## 🏗 프로젝트 구조

```text
backend/
├── app/
│   ├── api/
│   │   ├── auth.py           # 사용자 인증·프로필
│   │   ├── certs.py          # 자격증 조회·검색 (Standard)
│   │   ├── fast_certs.py     # Redis 기반 초고속 조회
│   │   ├── ai_recommendations.py  # AI 추천 (Hybrid RAG 연동)
│   │   ├── recommendations.py    # 전공·AI 기반 추천
│   │   ├── jobs.py, majors.py, favorites.py, acquired_certs.py, admin.py, contact.py
│   │   └── deps.py
│   ├── rag/                  # RAG 검색·생성
│   │   ├── api/routes.py     # POST /rag/ask
│   │   ├── config.py         # RAG 하이퍼파라미터
│   │   ├── retrieve/hybrid.py      # BM25+Vector+Contrastive RRF, Query Routing, Gating
│   │   ├── retrieve/metadata_soft_score.py   # 직무·전공·분야 가산/감점
│   │   ├── rerank/cross_encoder.py # Reranker HF Space API (CertFinder Reranker)
│   │   ├── generate/evidence_first.py, gating.py
│   │   ├── index/            # BM25·Vector 인덱스 빌드
│   │   ├── eval/             # Recall@k, MRR, nDCG, 골든 로더
│   │   └── utils/            # Dense rewrite, HyDE, CoT, personalized query
│   ├── services/
│   │   ├── vector_service.py # OpenAI Embedding
│   │   ├── fast_sync_service.py  # Redis 벌크 동기화
│   │   └── data_loader.py
│   ├── redis_client.py, database.py, models.py, schemas/, config.py
│   └── utils/ai.py, auth.py, stream_producer.py
├── scripts/                     # 평가·적용 검증·데이터 파이프라인
│   ├── eval_three_models_no_reranker.py   # 3모델 비교(baseline/current/enhanced_reranker), CSV·보고서
│   ├── eval_channel_ablation.py          # 채널별 K/가중치 Ablation
│   ├── eval_enhanced_only.py             # Enhanced 단일 파이프라인 평가
│   ├── eval_reranker_on_off.py           # 리랭커 ON/OFF 비교
│   ├── bench_apply_verification.py       # RAG 응답 크기·get_list 지연 측정
│   ├── export_rag_eval_metrics.py       # rag_eval_metrics_8.json (API /rag-eval-metrics용)
│   └── (기타) run_*_tuning.py, audit_corpus_*.py 등 — docs/README.md 참고
├── data/                     # 골든셋, 코퍼스, contrastive 학습 데이터
├── main.py
├── requirements.txt
└── .env.example
```

---

## ⚡ 주요 기술 스택

| 영역 | 내용 |
|------|------|
| **API** | FastAPI, Pydantic, SQLAlchemy, Supabase(PostgreSQL) |
| **캐시·속도** | Redis (orjson 직렬화), FastSyncService 부팅 시 전체 인덱스 로드, StreamProducer Pub/Sub |
| **RAG** | BM25 + Vector + Contrastive 3-way RRF/Linear Fusion, Query Routing, Dense Query Rewrite, Reranker(HF Space API), Metadata·개인화 Soft Score |
| **배포** | Render, UptimeRobot 모니터링 (규칙: `.cursor/rules/deployment.mdc` 참고) |

---

## 🔍 RAG 파이프라인 개요

1. **질의 처리**  
   Dense Query Rewrite(전공·학년·북마크·취득 반영), 짧은 쿼리 보조 키워드, Query Type 분류(키워드형/자연어형).

2. **검색**  
   - **BM25**: 한글 2-gram, 자격명 부스팅, 추천용 purpose/직무 필드.  
   - **Vector**: `certificates_vectors` OpenAI 임베딩 검색, 임계값·게이팅.  
   - **Contrastive**: 768-dim 질의·청크 임베딩(FAISS) 검색, Redis 캐시.  
   - **Query Routing**: 짧은 키워드 쿼리는 BM25 비중 확대, Vector 게이팅으로 오탐 억제.

3. **융합**  
   RRF(K=60) 또는 Linear Fusion으로 BM25·Vector·Contrastive 3-way 순위 병합 → 상위 N개 후보(기본 110).

4. **메타데이터·개인화**  
   직무/전공/목적 일치 가산, 분야 이탈 감점. (선택) 개인화 soft score.

5. **리랭커**  
   Reranker(HF Space API)로 후보 풀(기본 30) 재정렬 → 상위 4개 선택. Gating으로 확신 높은 질의는 리랭커 스킵(지연 절감).

6. **생성**  
   Evidence-first 프롬프트로 상위 청크 기반 답변 생성, Gating 조건 시 “근거 부족” 응답.

---

## 📈 RAG 고도화 방식 및 성과

기준: **골든셋**(예: `reco_golden_recommendation_18.jsonl` 등) 기준 Recall@k, Hit@k, MRR@k, nDCG@k.  
베이스라인 대비 아래 조합으로 단계적 개선을 적용했고, 수치는 동일 골든·환경에서의 상대적 변화를 반영합니다.

### 적용한 고도화 방식

| 구분 | 고도화 방식 | 설명 |
|------|-------------|------|
| **1. Hybrid 검색** | BM25 + Vector 병합 | 단일 벡터 검색 대비 키워드형·자연어형 모두 대응, Recall·Hit 상승. |
| **2. RRF / Linear Fusion** | RRF K=60, 또는 Linear(λ*BM25+(1-λ)*Vector) | R@20·Hit@20·MRR@4 극대화를 위해 K·가중치 튜닝. Linear 적용 시 지표 추가 상승. |
| **3. Vector 임계값** | `RAG_VECTOR_THRESHOLD=0.02` | 저유사도 노이즈 제거. RRF 구간에서 MRR·nDCG 상승. |
| **4. 후보 풀 확대** | RRF Top-N 95 → 110 | MRR +3% 상승, 지연 +5% 수준(평가 스윕 기준). |
| **5. BM25 파라미터** | `b=0.5`, 한글 n-gram, 자격명 부스팅 | Hit@4·nDCG@20·nDCG@4 상승. |
| **6. Dense Query Rewrite** | 전공·학년·북마크·취득 반영 재질의 | Vector 채널 정확도·추천 적합도 향상. |
| **7. Query Routing + Gating** | 짧은 쿼리 BM25 강화, Vector min_score/gap 게이팅 | 짧은 키워드에서 Vector 오탐 억제, 상위 순위 보존. |
| **8. Reranker** | HF Space API(CertFinder Reranker), 풀 30→Top 4 | 최종 노출 순위 품질 향상. Reranker Gating으로 확신 높은 질의는 스킵해 지연 절감. |
| **9. Metadata Soft Score** | 직무·전공·목적 가산, 분야 이탈 감점 | RRF 후보 내 추천 적합 자격 상위 이동. |
| **10. 리랭커 입력 보강** | 쿼리에 전공·목적·직무, passage에 자격명 접두사 | Reranker가 문맥을 반영해 재정렬. |

### Current 모델 대비 성장

- **Current 모델**: 이전 실서비스 기준 — 벡터 단일 검색(certificates_vectors) + 임계값 0.4. BM25·RRF·리랭커 미적용.
- **고도화 모델(Enhanced)**: Hybrid RAG — BM25 + Vector + **Contrastive** 3-way RRF + Dense Rewrite + Metadata Soft Score. **리랭커 미적용**으로 측정.

동일 골든셋·동일 환경에서 **리랭커 없이** 측정한 Current 대비 성장은 아래와 같다.

| 지표 | Current (벡터 단일, 임계값 0.4) | 고도화 (Hybrid, 리랭커 미적용) | 성장 |
|------|---------------------------------|---------------------------------|------|
| **Recall@5** | 0.167 | 0.556 | **+233%** |
| **Recall@10** | 0.167 | 0.667 | **+300%** |
| **Recall@20** | 0.278 | 0.778 | **+180%** |
| **Hit@20** | 0.67 | 2.00 | **+200%** |
| **Success@4** | 0.333 | 0.667 | **+100%** |
| **MRR@4** | 0.083 | 0.667 | **+700%** |

- 위 수치는 동일 골든·환경에서의 측정 결과이며, 골든셋·질의 수에 따라 수치가 달라질 수 있다.

### 선택 적용·Ablation

- **HyDE**: Ablation에서 베이스라인 대비 상승했으나 운영에서는 오탐·비용 고려로 **기본 OFF**.
- **CoT / Step-back / BM25 PRF**: 방법론 확장용 옵션, 기본 OFF. 필요 시 `app/rag/config.py` 및 평가 스크립트로 비교 가능.

### 캐싱 전략 (Redis + LRU, RAG 전용)

RAG는 외부 API 호출(OpenAI, HF Space)과 대형 인덱스(FAISS, PostgreSQL)를 동시에 사용하기 때문에 **캐시 계층 설계가 곧 성능·비용·처리량 설계**입니다.

- **1단계: Query → Embedding 캐시 (Contrastive)**  
  - 위치: `app/rag/retrieve/contrastive_retriever.py`  
  - 키: Redis `contrastive:q2v:v1:{hash(query_text)}`  
  - 값: 정규화된 768-dim 벡터(list[float])  
  - TTL: 기본 **7일** (`_CONTRASTIVE_CACHE_TTL_SECONDS`)  
  - 무효화: Contrastive 모델/HF Space 교체 시 prefix(`v1`)만 올려 전체 무효화  
  - 효과 (골든 상위 8개, `top_k=20`, contrastive-only):  
    - Recall@20 / MRR@20: **0.8542 / 0.7708** (캐시 전후 동일)  
    - Avg_ms: **836.0 → 67.1 ms**  
    - P95_ms: **1600.0 → 43.2 ms**  
    → 동일 질의 재사용 시, 임베딩/검색 지연이 **약 10~20배 감소**.

- **2단계: Query + top_k → Contrastive 결과 캐시**  
  - 위치: `contrastive_retriever.contrastive_search()`  
  - 키: Redis `contrastive:results:v1:{hash(query_text, top_k)}`  
  - 값: `[[chunk_id, score], ...]` 형식의 상위 결과 리스트  
  - TTL: 기본 **7일**  
  - 무효화: FAISS 인덱스 리빌드/교체 시 prefix만 올려 전체 무효화  
  - 의미: HF Space 임베딩 + FAISS 검색까지 포함한 **완성된 후보 리스트**를 캐시하여, 동일 query/top_k 재요청 시 사실상 Redis read 수준 지연으로 응답.

- **3단계: (query, chunk_id) → Reranker score 캐시 (LRU + Redis)**  
  - 위치: `app/rag/rerank/cache.py` (`RerankerCache`), `app/rag/rerank/cross_encoder.py` (`_rerank_via_api`)  
  - 키:  
    - 로컬 LRU: `sha256(query ||| doc_hash)[:32]`  
    - Redis: `rerank:v1:{sha256(query ||| doc_hash)[:32]}`  
    - `doc_hash = sha256(passage_text)[:16]`  
  - 값: 단일 float score (또는 `{ "score": float }`)  
  - TTL: 기본 **1시간** (`RAG_RERANK_CACHE_TTL`, `.env`로 조절)  
  - 무효화: Reranker 모델/HF Space 교체 시 prefix(`v1`)만 올려 전체 무효화  
  - 동작:  
    1. 로컬 LRU → Redis 순서로 `(query, passage)` pair score 조회  
    2. miss인 pair만 HF Space로 batch 호출  
    3. 응답 score를 LRU + Redis에 동시에 기록  
  - 효과 (골든 상위 8개, `enhanced_reranker`, 3-way RRF 기준 2회차):  
    - Baseline(2-way) Avg_Latency_ms: **558.5 ms**  
    - Current(3-way) Avg_Latency_ms: **609.5 ms**  
    → contrastive + reranker까지 포함한 3-way에서도 **Baseline 대비 추가 지연이 ~50 ms 수준**으로 수렴.

- **4단계: RAG 응답 캐시 (질의 전체 응답)**  
  - 위치: `app/rag/retrieve/cache.py`, `redis_client.rag_ask_cache_key()`  
  - 키: `rag:ask:v1:{hash(query, filters, top_k, baseline_id)}`  
  - 값: RAG 전체 응답(JSON 직렬화, 모델 출력 포함)  
  - TTL: `RAG_CACHE_TTL` (기본 600초)  
  - 용도: 동일 질의/필터 조합에 대해 **전체 RAG 파이프라인 실행 자체를 건너뛰는 계층**으로, 반복 질의가 많은 환경에서 처리량(throughput)을 크게 끌어올림.

정리하면,

- **Contrastive**: Query→Embedding + Query+top_k→Results 두 레이어 캐시로 HF Space 호출·FAISS 검색을 크게 줄이면서, 검색 품질(Recall/MRR)은 그대로 유지.  
- **Reranker**: (query, passage) pair-level 캐시(LRU+Redis)로 동일 passage 재랭킹 비용을 제거하고, 후보 풀 구성이 조금 바뀌어도 재사용.  
- **전체 RAG**: Query+Filters+top_k+baseline_id 단위 응답 캐시로, 자주 반복되는 추천 질의에 대해 end-to-end RAG 실행을 피함.

---

## 🛠 실행 방법

1. **환경**  
   `.env` 설정 (참고: `.env.example`).  
   Python: `uv` 사용 시 `uv run`으로 실행.

2. **의존성**  
   `pip install -r requirements.txt` 또는 `uv pip install -r requirements.txt`

3. **서버**  
   `cert-app/backend` 디렉터리에서 `uvicorn main:app --reload`. (uv 미사용 시 venv의 `python -m uvicorn main:app --reload`)

4. **RAG 인덱스**  
   BM25: `python -m app.rag index`. Vector: Supabase `certificates_vectors`. Contrastive: FAISS 인덱스·Redis 캐시(설정 시 `docs/README.md` §3 참고).

---

## 📊 평가 및 골든셋

- **표준 골든셋 (이 골든으로 평가)**: `data/reco_golden_recommendation_18.jsonl`
  - **형식**: 질문은 **직무 희망만** (예: "데이터 분석 쪽으로 가고싶어"). 학년·학과·취득/북마크는 **프로필**에서 재질의에 반영.
  - **건수**: n=34 (프로필 없음 16건 + 프로필 있음 18건, IT·비IT 혼합). **모든 RAG 평가는 이 골든셋 기준.**
- **3모델 비교 (리랭커 없음)**  
  `cd cert-app/backend` 후  
  `uv run python scripts/eval_three_models_no_reranker.py --golden data/reco_golden_recommendation_18.jsonl --output data/eval_three_models_8.csv --report data/eval_three_models_8_report.md`  
  → baseline(Vector만) / current(Dense+Sparse RRF) / enhanced_reranker(BM25+Vector+Contrastive+RRF) 지표·개선률 출력. 전체 골든(34건) 또는 `--max-queries 8` 등으로 실행.
- **적용 검증 (RAG 응답 크기·DB 지연)**  
  `uv run python scripts/bench_apply_verification.py` (backend 디렉터리에서 실행)
- **RAG 평가 메트릭 JSON (API용)**  
  `uv run python scripts/export_rag_eval_metrics.py` → `data/rag_eval_metrics_8.json` (GET /api/v1/recommendations/ai/rag-eval-metrics에서 사용)

- **백엔드 문서 (통합)**: `docs/README.md` — CertFinder RAG 성능 지표(적용 전/후, 캐시, 복구), 운영 기본값·평가 절차, Contrastive §3. 상세: `docs/PERFORMANCE_IMPROVEMENT_METRICS.md`.

---

## 📁 데이터·스크립트

| 용도 | 파일·스크립트 |
|------|----------------|
| **골든셋** | `data/reco_golden_recommendation_18.jsonl` (표준 평가용). 평가 결과: `data/eval_three_models_8.csv`, `data/eval_three_models_8_report.md` |
| **RAG 평가 메트릭** | `scripts/export_rag_eval_metrics.py` → `data/rag_eval_metrics_8.json` (API 노출) |
| **RAG 코퍼스·리랭커** | `data/all_cert_corpus.json`, `data/reranker_train_from_contrastive.jsonl` 등. 정제·품질 검사·코퍼스 검토 스크립트는 `scripts/` 및 `docs/README.md` 참고. |

---

## 📚 참고 문서

- **백엔드 문서 (통합)**: `docs/README.md` — CertFinder RAG 성능 지표·적용 검증·운영 기본값·Contrastive §3.
- **트러블슈팅**: `docs/TRUBLESHOOTING.md` — 병목·타임아웃·예외 로깅·체크리스트.
- **성능 개선 지표 (상세)**: `docs/PERFORMANCE_IMPROVEMENT_METRICS.md` — DB 쿼리·Reranker·복구 절차.
- **배포·CORS·환경변수**: `.cursor/rules/deployment.mdc`
- **리랭커 데이터 품질**: `data/RERANKER_TRAIN_QUALITY_REVIEW.md`, `data/ANALYSIS_SCRIPTS_AUDIT.md`

---

## Reranker

- **CertFinder Reranker**: HF Hub 모델·Space API로 서빙. 환경변수 `RAG_RERANKER_MODEL_REPO_ID`, `RAG_RERANKER_SPACE_REPO_ID`, `RAG_RERANKER_API_URL` 참고.
- **역할**: RRF 상위 30개 후보 재정렬 → Top 4 선택. Gating 적용 시 확신 높은 질의는 스킵.
