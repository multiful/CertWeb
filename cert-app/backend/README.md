# CertFinder Backend

고성능 비동기 자격증 분석·추천 API 서버. **Hybrid RAG**(BM25 + Vector + RRF + Reranker) 기반 자격증 검색·추천과 Redis 기반 초고속 조회를 제공합니다.

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
│   │   ├── retrieve/hybrid.py      # BM25+Vector RRF, Query Routing, Gating
│   │   ├── retrieve/metadata_soft_score.py   # 직무·전공·분야 가산/감점
│   │   ├── rerank/cross_encoder.py # Cross-Encoder 리랭커 (Dongjin-kr/ko-reranker)
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
├── scripts/
│   ├── populate_certificates_vectors.py  # RAG용 certificates_vectors 채우기
│   ├── clean_contrastive_dataset.py      # Contrastive 학습 데이터 정제 (qual_id, 5 neg, dedup)
│   ├── clean_contrastive_dataset_v2.py   # v2: bad negative 교체, 의미 검증, audit
│   ├── eval_hybrid_baseline.py, eval_by_query_type.py, run_dense_ablation.py
│   ├── build_all_cert_corpus.py, align_contrastive_qual_ids_to_supabase.py
│   └── compare_rag_three_way.py, eval_hyde_ablation.py, ...
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
| **RAG** | BM25(한글 n-gram) + OpenAI Embedding, RRF/Linear Fusion, Query Routing, Dense Query Rewrite, Cross-Encoder Reranker(ko-reranker), Metadata·개인화 Soft Score |
| **배포** | Render, UptimeRobot 모니터링 (규칙: `.cursor/rules/deployment.mdc` 참고) |

---

## 🔍 RAG 파이프라인 개요

1. **질의 처리**  
   Dense Query Rewrite(전공·학년·북마크·취득 반영), 짧은 쿼리 보조 키워드, Query Type 분류(키워드형/자연어형).

2. **검색**  
   - **BM25**: 한글 2-gram, 자격명 부스팅, 추천용 purpose/직무 필드.  
   - **Vector**: `certificates_vectors` dense_content 임베딩 검색, 임계값·게이팅.  
   - **Query Routing**: 짧은 키워드 쿼리는 BM25 비중 확대, Vector 게이팅으로 오탐 억제.

3. **융합**  
   RRF(Reciprocal Rank Fusion) 또는 Linear Fusion으로 BM25·Vector 순위 병합 → 상위 N명 후보(기본 95).

4. **메타데이터·개인화**  
   직무/전공/목적 일치 가산, 분야 이탈 감점. (선택) 개인화 soft score.

5. **리랭커**  
   Cross-Encoder(ko-reranker)로 후보 풀(기본 30) 재정렬 → 상위 4개 선택. Gating으로 확신 높은 질의는 리랭커 스킵(지연 절감).

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
| **2. RRF / Linear Fusion** | RRF K=30, 또는 Linear(λ*BM25+(1-λ)*Vector) | R@20·Hit@20·MRR@4 극대화를 위해 K·가중치 튜닝. Linear 적용 시 지표 추가 상승. |
| **3. Vector 임계값** | `RAG_VECTOR_THRESHOLD=0.025` | 저유사도 노이즈 제거. RRF 구간에서 **MRR@4 0.809 → 0.838** 상승. |
| **4. 후보 풀 확대** | RRF Top-N 90 → 95 | nDCG@20 소폭 상승 유지. |
| **5. BM25 파라미터** | `b=0.5`, 한글 n-gram, 자격명 부스팅 | Hit@4·nDCG@20·nDCG@4 상승. |
| **6. Dense Query Rewrite** | 전공·학년·북마크·취득 반영 재질의 | Vector 채널 정확도·추천 적합도 향상. |
| **7. Query Routing + Gating** | 짧은 쿼리 BM25 강화, Vector min_score/gap 게이팅 | 짧은 키워드에서 Vector 오탐 억제, 상위 순위 보존. |
| **8. Cross-Encoder Reranker** | Dongjin-kr/ko-reranker, 풀 30→Top 4 | 최종 노출 순위 품질 향상. Reranker Gating으로 확신 높은 질의는 스킵해 지연 절감. |
| **9. Metadata Soft Score** | 직무·전공·목적 가산, 분야 이탈 감점 | RRF 후보 내 추천 적합 자격 상위 이동. |
| **10. 리랭커 입력 보강** | 쿼리에 전공·목적·직무, passage에 자격명 접두사 | Reranker가 문맥을 반영해 재정렬. |

### Current 모델 대비 성장

- **Current 모델**: 이전 실서비스 기준 — 벡터 단일 검색(certificates_vectors) + 임계값 0.4. BM25·RRF·리랭커 미적용.
- **고도화 모델(Enhanced)**: Hybrid RAG — BM25 + Vector + RRF + Dense Rewrite + Metadata Soft Score. **리랭커 미적용**으로 측정.

동일 골든셋·동일 환경에서 **리랭커 없이** 측정한 Current 대비 성장은 아래와 같다.

| 지표 | Current (벡터 단일, 임계값 0.4) | 고도화 (Hybrid, 리랭커 미적용) | 성장 |
|------|---------------------------------|---------------------------------|------|
| **Recall@5** | 0.167 | 0.556 | **+233%** |
| **Recall@10** | 0.167 | 0.667 | **+300%** |
| **Recall@20** | 0.278 | 0.778 | **+180%** |
| **Hit@20** | 0.67 | 2.00 | **+200%** |
| **Success@4** | 0.333 | 0.667 | **+100%** |
| **MRR@4** | 0.083 | 0.667 | **+700%** |

- 측정: `uv run python scripts/eval_current_vs_enhanced.py --golden data/reco_golden_hard3.jsonl --out data/current_vs_enhanced.json` (골든 `reco_golden_hard3.jsonl`, n=3).
- 재측정: `--golden data/reco_golden_recommendation_18.jsonl` 등 다른 골든으로 실행하면 질의 수·도메인에 따라 수치가 달라진다.

### 선택 적용·Ablation

- **HyDE**: Ablation에서 베이스라인 대비 상승했으나 운영에서는 오탐·비용 고려로 **기본 OFF**.
- **CoT / Step-back / BM25 PRF**: 방법론 확장용 옵션, 기본 OFF. 필요 시 `app/rag/config.py` 및 평가 스크립트로 비교 가능.

---

## 🛠 실행 방법

1. **환경**  
   `.env` 설정 (참고: `.env.example`).  
   Python: `uv` 사용 시 `uv run`으로 실행.

2. **의존성**  
   `pip install -r requirements.txt` 또는 `uv pip install -r requirements.txt`

3. **서버**  
   `uvicorn main:app --reload`  
   (규칙: `.cursor/rules/use-uv.mdc`에 따라 venv 내 `uv` 경로 사용 가능)

4. **RAG 인덱스**  
   BM25·Vector 인덱스 갱신:  
   `uv run python scripts/populate_certificates_vectors.py`  
   `python -m app.rag index` (BM25 인덱스 빌드)

---

## 📊 평가 및 골든셋

- **표준 골든셋**: `data/reco_golden_recommendation_18.jsonl` (18질의). 확장 골든은 `data/reco_golden_*.jsonl` 등.
- **Hybrid 베이스라인 (Reranker OFF/ON)**  
  `uv run python scripts/eval_hybrid_baseline.py --golden data/reco_golden_recommendation_18.jsonl`
- **질의 유형별 Recall/MRR**  
  `uv run python scripts/eval_by_query_type.py` (골든 경로는 스크립트 인자 참고)
- **Dense Ablation**  
  `uv run python scripts/run_dense_ablation.py --golden data/reco_golden_recommendation_18.jsonl [--max-queries N] [--output-csv path]`
- **3축 비교 (베이스라인 / 현재 / 고도화)**  
  `uv run python scripts/compare_rag_three_way.py`

상세 운영 기본값·평가 절차: `docs/DENSE_VECTOR_OPERATIONAL_DEFAULTS.md` (해당 문서가 있는 경우).

---

## 📁 데이터·스크립트

| 용도 | 파일·스크립트 |
|------|----------------|
| **RAG 코퍼스** | `data/all_cert_corpus.json` (Supabase export 기반: `scripts/build_all_cert_corpus.py --from-db`) |
| **Contrastive 학습** | `data/contrastive_profile_train_merged_supabase_ids.json` |
| **정제 v1** | `uv run python scripts/clean_contrastive_dataset.py --train data/... --corpus data/all_cert_corpus.json` → qual_id 보정, negative 5개, dedup, audit |
| **정제 v2** | `uv run python scripts/clean_contrastive_dataset_v2.py --train data/... --corpus data/all_cert_corpus.json` → bad negative 교체, negative_type 의미 검증, positive 확장 플래그, 템플릿 중복 탐지, audit |
| **Contrastive 검증** | `uv run python scripts/validate_contrastive_dataset.py --samples data/...` |
| **qual_id 정렬** | `scripts/align_contrastive_qual_ids_to_supabase.py` (corpus 기준 qual_id 매핑) |

---

## 📚 참고 문서

- **RAG 고도화 가이드**: `RAG_IMPROVEMENT.md` — 벡터 vs 키워드 진단, 청킹·벡터·키워드·리랭커 순서, Gating·캐시, RAGAS 등.
- **배포·CORS·환경변수**: `.cursor/rules/deployment.mdc`
- **Reranker (HF Space)**: `scripts/hf_space_reranker/README.md`
- **all_cert_corpus 빌드**: `scripts/README_ALL_CERT_CORPUS.md`

---

## Reranker

- **모델**: Dongjin-kr/ko-reranker (Cross-Encoder)
- **역할**: RRF 상위 30개 후보 재정렬 → Top 4 선택. Gating 적용 시 확신 높은 질의는 스킵.
