# CertFinder Backend

**CertFinder** 자격증 검색·추천 API 백엔드. 고성능 비동기 서버로, **Hybrid RAG**(BM25 + Vector + Contrastive 3-way RRF + Reranker) 기반 검색·추천과 Redis 기반 초고속 조회를 제공합니다.

---

## 목차

- [프로젝트 구조](#-프로젝트-구조)
- [주요 기술 스택](#-주요-기술-스택)
- [RAG 파이프라인 개요](#-rag-파이프라인-개요)
- [RAG 기능 전체 목록 (문서)](#-rag-기능-전체-목록-문서)
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
│   │   ├── api/routes.py     # RAG HTTP 라우트
│   │   ├── config.py         # RAG 하이퍼파라미터 (RAGSettings)
│   │   ├── retrieve/hybrid.py      # BM25+Vector+Contrastive 융합, 라우팅, soft, 리랭커
│   │   ├── retrieve/metadata_soft_score.py   # 메타데이터 soft (옵션)
│   │   ├── retrieve/personalized_soft_score.py  # 개인화 soft (프로필 시)
│   │   ├── rerank/cross_encoder.py # Reranker HF Space API (CertFinder Reranker)
│   │   ├── generate/evidence_first.py, gating.py
│   │   ├── index/            # BM25·Vector 인덱스 빌드
│   │   ├── eval/             # Recall@k, MRR, nDCG, 골든 로더
│   │   └── utils/            # Dense rewrite, HyDE, CoT, domain_tokens, …
│   ├── docs/                 # RAG_FEATURES.md 등
│   ├── services/
│   │   ├── vector_service.py # OpenAI Embedding
│   │   ├── fast_sync_service.py  # Redis 벌크 동기화
│   │   └── data_loader.py
│   ├── redis_client.py, database.py, models.py, schemas/, config.py
│   └── utils/ai.py, auth.py, stream_producer.py
├── scripts/                     # 데이터·평가 파이프라인
│   ├── ab_golden_hybrid_tuning.py       # 골든 hybrid A/B (enhanced만, CE off)
│   ├── ab_golden_personalized_soft.py   # 개인화 soft ON/OFF 골든 A/B
│   ├── run_rag_golden_ab.py             # hybrid A/B 위임
│   ├── build_rewrite_snapshot.py        # 골든 → 재질의 스냅샷
│   ├── build_intent_labels_init.py      # audit → intent_labels_init.json
│   └── upload_intent_labels_to_supabase.py
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
| **배포** | Railway(API), Vercel(프론트), UptimeRobot 등 `/health` 모니터링 (`.cursor/rules/deployment.mdc`) |

---

## 🔍 RAG 파이프라인 개요

> **기능 전체 목록(표·모듈 맵)**: [`docs/RAG_FEATURES.md`](docs/RAG_FEATURES.md) — 구현된 `RAG_*` 스위치·채널·캐시·평가 CLI를 한곳에 정리.  
> **인덱싱·재색인**: `RAG_Indexing.md` · **E2E(ask)**: `data/rag_e2e_pipeline.md` · **개선 이력**: `RAG_IMPROVEMENT.md`

1. **질의 처리**  
   Dense Query Rewrite(전공·학년·북마크·취득 반영), 짧은 쿼리 보조 키워드, Query Type 분류(DB 라벨 또는 폴백), 식별자 위주 질의 시 확장·rewrite 스킵, pre-retrieval 예산(옵션).

2. **검색**  
   - **BM25**: 디스크 `bm25.pkl`, 한글 2-gram, 자격명 부스팅, 쿼리 확장 규칙.  
   - **계층 BM25(옵션)**: `content` 문단 단위 child 검색 → `qual_id` 환원 후 BM25 채널과 블렌드(`RAG_HIERARCHICAL_*`).  
   - **Vector**: `certificates_vectors` pgvector, 원문+rewrite 다중 검색·키워드 확장 벡터(설정 시).  
   - **Contrastive**: 768-dim FAISS/원격 임베딩, Redis 캐시.  
   - **Query Routing**: 짧은 키워드형에서 BM25 비중·벡터 게이팅.  
   - **Contrastive 게이팅**: `RAG_CONTRASTIVE_ALLOWED_QUERY_TYPES` — DB 라벨이 없을 때 폴백 타입만 허용되도록 목록을 맞출 것.

3. **융합**  
   **Linear**(기본) / CombSum / CombMNZ, `RAG_RRF_K`·채널 가중·쿼리타입별 linear 3-way 가중. 후보 풀: `RAG_TOP_N_CANDIDATES` 등(기본 88 전후, `.env`로 조정).

4. **메타데이터·개인화**  
   **메타 soft**(옵션, 기본 OFF): 직무·전공·도메인 가산/감점. **개인화 soft**(프로필 시): 전공·즐겨찾기 분야·취득 감점·학년-난이도 등. **취득 hard exclude** 옵션.

5. **리랭커**  
   Cross-Encoder HF Space API(기본 OFF). 풀 크기·게이팅·입력 보강·pair 캐시.

6. **생성**  
   Evidence-first 프롬프트·Gating(근거 부족 응답).

---

## 📑 RAG 기능 전체 목록 (문서)

- **[`docs/RAG_FEATURES.md`](docs/RAG_FEATURES.md)**  
  채널·융합·soft·캐시·실험 플래그·디렉터리 맵·자주 쓰는 스크립트를 표로 정리. 코드와 달라질 때는 `app/rag/config.py`를 기준으로 본 문서를 갱신한다.

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
| **11. Contrastive 게이팅** | `RAG_CONTRASTIVE_ALLOWED_QUERY_TYPES` (natural, purpose_only, roadmap 등) | Contrastive를 잘 쓰는 타입만 arm 활성화, 키워드/자격명 쿼리에서는 비활성 → 비용·노이즈 절감. |
| **12. 쿼리 타입별 Contrastive RRF 가중치** | `RAG_QUERY_TYPE_CONTRASTIVE_WEIGHTS_ENABLE` + `CONTRASTIVE_QUERY_TYPE_WEIGHTS` | 자연어·로드맵 계열은 Contrastive 비중 강화, 키워드/자격명은 약화 → 3-way RRF 품질 유지·Contrastive 단일 성능 크게 상승. |

### 저장된 고도화 기준 및 채널 Ablation

- **저장 기준**: `data/enhanced_saved_baseline.json`(설정·16지표), `data/eval_enhanced_baseline_snapshot.json`(튜닝 스냅샷). 추가 고도화는 이 기준 대비 적용·롤백 판단.
- **채널별 기여도**: `scripts/eval_channel_ablation.py` → `data/channel_ablation.csv`, `data/channel_ablation_report.md`.  
  BM25 only / Vector only / Contrastive only vs 3-way(enhanced_reranker) 비교. Contrastive는 게이팅·타입별 가중치 적용 후 단일 Recall@5·MRR이 크게 상승.
- **고도화 전략**: BM25·Vector·Contrastive **단일 성능**을 올린 뒤, **RRF weight/게이팅 재튜닝**을 병행해야 RRF가 이득을 제대로 반영. 단일 악화 또는 RRF 악화 시 해당 변경은 적용하지 않음.

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
- **최신 수치**: `data/eval_three_models_8_report.md`, `data/eval_three_models_8.csv` (전체 골든 기준) 참고.

### 선택 적용·Ablation

- **HyDE**: Ablation에서 베이스라인 대비 상승했으나 운영에서는 오탐·비용 고려로 **기본 OFF**.
- **CoT / Step-back / BM25 PRF**: 방법론 확장용 옵션, 기본 OFF. 필요 시 `app/rag/config.py` 및 평가 스크립트로 비교 가능.

### 캐싱 전략 (Redis + LRU, RAG 전용)

RAG는 외부 API 호출(OpenAI, HF Space)과 대형 인덱스(FAISS, PostgreSQL)를 동시에 사용하기 때문에 **캐시 계층 설계가 곧 성능·비용·처리량 설계**입니다.

- **1단계: Query → Embedding 캐시 (Contrastive)**  
  - 위치: `app/rag/retrieve/contrastive_retriever.py`  
  - 키: Redis `contrastive:q2v:v1:{hash(query_text)}`  
  - 값: 정규화된 768-dim 벡터(list[float])  
  - TTL: 기본 **12시간** (`_CONTRASTIVE_Q2V_CACHE_TTL_SECONDS`)  
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
  - TTL: 기본 **24시간** (`_CONTRASTIVE_RESULTS_CACHE_TTL_SECONDS`)  
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

- **표준 골든셋 (이 골든으로 평가)**: `dataset/reco_golden_recommendation_19_clean.jsonl`
  - **형식**: 질문은 **직무 희망만** (예: "데이터 분석 쪽으로 가고싶어"). 학년·학과·취득/북마크는 **프로필**에서 재질의에 반영.
  - **레거시 참고**: `data/reco_golden_recommendation_18.jsonl` (과거 n=34 스펙). **현재 A/B·트리거는 19_clean 기준** (`RAG_Indexing.md`, `RAG_TOP_N_CANDIDATES` 주석 등).
- **3모델 비교 (리랭커 없음)**  
  `cd cert-app/backend` 후  
  `uv run python -m app.rag.eval --golden dataset/reco_golden_recommendation_19_clean.jsonl [--output dataset/eval_reco_golden_19_clean_enhanced.csv] [--max-queries N]`  
  → baseline(단일 Vector) / current(2-way 레거시) / current_reranker / enhanced_reranker(3-way BM25+Vector+Contrastive RRF+리랭커) 4-way 비교.
- **재질의 스냅샷**: `uv run python scripts/build_rewrite_snapshot.py` → `data/reco_golden_recommendation_18_rewrite_snapshot.jsonl`
- **intent_labels 갱신**: `uv run python scripts/build_intent_labels_init.py` 후 `uv run python scripts/upload_intent_labels_to_supabase.py`
- **3-way linear fusion 튜닝 (LONG/EXACT 가중치)**: `python scripts/eval_linear_qt_sweep.py` — 골든 부분셋으로 `RAG_LINEAR_QT_LONG_W_*` 등 env 오버라이드를 서브프로세스 스윕. 평가 시 `RAG_EVAL_TOP_K`(기본 10)로 Recall@5/10·MRR_qual 관측 길이를 맞춘다.
- **개선 축 순차 A/B (스윕 아님)**: `python scripts/eval_sequential_axis_ablation.py` — 메타 도메인 감점/PRF/dense 확장/BM25 옵션 등을 **하나씩** 쌓아 보며 복합(2×R@5_qual+MRR_qual)이 오를 때만 채택. 결과는 `reports/sequential_axis_ablation_YYYY-MM-DD.md`.
- **linear 후 BM25 순위 prior**: `RAG_LINEAR_BM25_RANK_PRIOR`(기본 0.008) — 3-way linear 병합 직후 BM25 상위 후보에 소량 가산. A/B는 `reports/bm25_rank_prior_ablation_2026-03-21.md` 참고.
- **원문+재작성 이중 벡터 RRF** (`get_vector_search`·`use_rewrite=True` 경로): `RAG_DUAL_VECTOR_RRF_WHEN` — `divergence`(기본), `legacy_non_it_only`, `off`. **하이브리드 메인**은 `dense_query`를 쓰며 `RAG_DENSE_MULTI_QUERY_ENABLE`이 켜져 있으면 원문+재작성을 이미 병합함(선형 fusion); 본 설정은 베이스라인 벡터-only·RAG `/ask`의 `baseline` 브랜치 등에 주로 영향.
- **메타 soft 이후 BM25 prior**: `RAG_POST_METADATA_BM25_RANK_PRIOR`(기본 0.004) — 메타데이터 가산/감점으로 순위가 뒤집힌 뒤, BM25 상위 후보를 한 번 더 약하게 보정(메타 soft가 실제 적용된 경우만).

---

## 📁 데이터·스크립트

| 용도 | 파일·스크립트 |
|------|----------------|
| **골든셋** | **`dataset/reco_golden_recommendation_19_clean.jsonl`** (표준). 레거시: `data/reco_golden_recommendation_18.jsonl`, `data/reco_golden_recommendation_18_rewrite_snapshot.jsonl` (재질의 스냅샷) |
| **평가 결과** | 예: `dataset/eval_reco_golden_19_clean_enhanced.csv` (`python -m app.rag.eval --golden dataset/reco_golden_recommendation_19_clean.jsonl --output ...`) |
| **intent_labels** | `data/intent_labels_init.json` (audit 기반 job/purpose), `scripts/upload_intent_labels_to_supabase.py`로 Supabase 반영 |
| **3-way RAG** | `data/contrastive_cleaned_audit_v3.json` (intent 초기값 추출), `data/contrastive_index/` (FAISS), `data/domain_tokens_new_cert_full.json` (넓은 도메인·overrides) |
| **Contrastive triplets (파인튜닝)** | 쿼리-only 생성: `scripts/generate_contrastive_triplets_from_queries.py` + `dataset/contrastive_queries.jsonl`. 최종 산출: `dataset/contrastive_train_triplets.jsonl` (refine·deleak 후). 절차·파일명은 `docs/CONTRASTIVE_TRAINING_DATA.md`. |
| **리랭커** | `data/reranker_train_from_contrastive.jsonl` (학습 데이터). 어려운 쿼리(통번역/빅데이터 분석가) 패치는 `scripts/patch_reranker_train_hard_queries.py`로 추가됨. |

---

## 📚 참고 문서

- **RAG 기법 요약서(프로젝트 종료본)**: [`docs/RAG_TECHNIQUES_SUMMARY.md`](docs/RAG_TECHNIQUES_SUMMARY.md)
- **RAG 기능 카탈로그(표·모듈)**: [`docs/RAG_FEATURES.md`](docs/RAG_FEATURES.md)
- **인덱싱**: `RAG_Indexing.md` · **E2E 파이프라인**: `data/rag_e2e_pipeline.md` · **개선 이력**: `RAG_IMPROVEMENT.md`
- **Contrastive**: `app/rag/contrastive/README.md`, `data/contrastive_index/README.md`
- **배포·CORS·환경변수**: `.cursor/rules/deployment.mdc`

---

## Reranker

- **CertFinder Reranker**: HF Hub 모델·Space API로 서빙. 환경변수 `RAG_RERANKER_MODEL_REPO_ID`, `RAG_RERANKER_SPACE_REPO_ID`, `RAG_RERANKER_API_URL` 참고.
- **역할**: RRF/융합 상위 풀(`RAG_RERANK_POOL_SIZE`, 기본 20 전후) 재정렬 → Top-k 선택. Gating 적용 시 확신 높은 질의는 스킵.
- **평가**: 기본은 리랭커 **미적용**으로 3모델·채널 Ablation 지표 측정. 리랭커 ON/OFF 비교는 `scripts/eval_reranker_on_off.py` 및 `docs/RERANKER_LATENCY_AND_METRICS.md` 참고.
- **베이스라인 vs RRF 고도화 비교표**: `scripts/eval_baseline_vs_enhanced.py` — Vector만(baseline) vs BM25+Vector+Contrastive+RRF+리랭커(enhanced). 전체 골든 사용 시 `--max-queries` 생략. 결과: `data/eval_baseline_vs_enhanced.json`.
