"""RAG 하이퍼파라미터: top_k, alpha, thresholds, rerank 경로, 캐시 TTL 등."""
from contextvars import ContextVar, Token
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Optional, Union

from pydantic import field_validator
from pydantic_settings import BaseSettings


def _optional_float(v: Union[str, float, int, None]) -> Optional[float]:
    """문자열이 숫자가 아니면 None (문서 예시 등이 .env에 들어간 경우 대비)."""
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


class RAGSettings(BaseSettings):
    """RAG 전용 설정. 환경변수 RAG_* 로 오버라이드."""

    # Retrieval: RRF Top30 → Reranker Top4 (Vector 단일 채널 고도화: 후보 확대)
    RAG_TOP_K: int = 4  # 최종 반환/생성에 사용할 청크 수 (reranker 출력)
    # `app.rag.eval.runner.run_eval_three_way` 전용: 평가 시 실제로 상위 몇 개까지 반환할지.
    # 과거 top_k=4 고정이면 Recall@5/10·MRR_qual 이름과 불일치(최대 4슬롯만 관측)하므로 기본 10.
    RAG_EVAL_TOP_K: int = 10
    # 기본값: 전체 골든(54) 오프라인 A/B에서 control(레거시)이 Recall/MRR/Hit 기준 우세.
    # 튜닝 후보는 RAG_CHALLENGER_PRESET + .env / scripts/eval_retrieval_ab_compare.py 로 검증 후 반영.
    RAG_TOP_N_CANDIDATES: int = 136
    RAG_RRF_K: int = 60
    RAG_RRF_EXPONENT: float = 1.0  # RRF 지수 p. 1=표준 1/(k+rank), >1이면 상위 순위 강조 1/(k+rank)^p. 2~3 실험 권장.
    # "linear" | "combsum" | "combmnz". (rrf 설정 시 코드에서 linear로 취급)
    # linear = min-max 정규화 가중합. 기본값 linear 확정.
    RAG_FUSION_METHOD: str = "linear"
    # linear 시 정규화된 점수에 적용할 지수. 1=기본, >1이면 높은 점수 강조(norm^p 후 가중합).
    # Query-type adaptive weighted linear 랜덤서치 결과, exponent=1.0 이 CombMNZ 및 과거 선형 기준 대비
    # Recall@5/10/20, Success@4, MRR@4 전 지표에서 우수해 기본값 1.0으로 고정.
    RAG_LINEAR_NORM_EXPONENT: float = 1.0
    # linear fusion 직후: BM25 목록 내 순위가 높을수록 소량 가산(MRR·Recall 안정화).
    RAG_LINEAR_BM25_RANK_PRIOR: float = 0.009
    RAG_POST_METADATA_BM25_RANK_PRIOR: float = 0.0055
    # 3-way linear fusion 가중치 오버라이드(세 값 모두 설정 시에만 적용, 합으로 정규화).
    # 비우면 hybrid.py의 LINEAR_QT_WEIGHTS_EXACT / LINEAR_QT_WEIGHTS_LONG 상수 사용.
    RAG_LINEAR_QT_EXACT_W_BM25: Optional[float] = None
    RAG_LINEAR_QT_EXACT_W_DENSE: Optional[float] = None
    RAG_LINEAR_QT_EXACT_W_CONTRASTIVE: Optional[float] = None
    RAG_LINEAR_QT_LONG_W_BM25: Optional[float] = None
    RAG_LINEAR_QT_LONG_W_DENSE: Optional[float] = None
    RAG_LINEAR_QT_LONG_W_CONTRASTIVE: Optional[float] = None
    RAG_VECTOR_TOP_N_OVERRIDE: Optional[int] = None  # 설정 시 벡터만 이 수만큼 뽑음. 100 실험 시 지표 동일·비용만 증가해 미적용
    RAG_ALPHA: float = 0.5  # hybrid: alpha*bm25_norm + (1-alpha)*vector_norm
    RAG_VECTOR_THRESHOLD: float = 0.008
    RAG_BM25_TOP_N: Optional[int] = 76
    RAG_CONTRASTIVE_TOP_N: Optional[int] = 76
    # Hierarchical retrieval: child(문단/섹션) BM25 검색 후 parent(qual_id)로 환원해 BM25 채널과 병합.
    # certificates_vectors.content가 채워진 행이 있을 때 recall 개선. 첫 빌드 시 메모리 BM25 구축 비용 있음.
    RAG_HIERARCHICAL_RETRIEVAL_ENABLE: bool = True
    RAG_HIERARCHICAL_CHILD_TOP_N: int = 90
    RAG_HIERARCHICAL_BLEND_WEIGHT: float = 0.38

    # CombMNZ 전용 설정: 정규화/zero 판정 방식
    # - norm_mode: "minmax" (채널별 min-max 정규화; 기존 동작) 또는 "rank" (순위 기반 1/(k+rank)^p 점수화)
    # - zero_mode:
    #   * "topn": 채널 리스트에 등장하면 nz=1로 간주 (기존 CombMNZ 정의와 동일)
    #   * "threshold": 정규화 점수가 threshold 이상일 때만 nz=1
    # 기본값들은 현재 구현과 동일한 동작을 재현하도록 설정.
    RAG_COMBMNZ_NORM_MODE: str = "minmax"
    RAG_COMBMNZ_ZERO_MODE: str = "topn"
    RAG_COMBMNZ_ZERO_THRESHOLD: float = 0.0
    # rank 기반 정규화 시 지수 p. 1=표준 1/(k+rank), >1이면 상위 순위 강조.
    RAG_COMBMNZ_RANK_EXPONENT: float = 1.0
    # query_type별 CombMNZ 채널 가중치 사용 여부 및 매핑(JSON 문자열).
    # 예시: {"natural": {"bm25":1.0,"dense":1.0,"contrastive":1.1}, "keyword":{"bm25":1.2,"dense":0.8,"contrastive":0.7}}
    RAG_COMBMNZ_QUERY_TYPE_WEIGHTS_ENABLE: bool = False
    RAG_COMBMNZ_QUERY_TYPE_WEIGHTS: str = ""

    # 랜덤 서치로 찾은 최적 가중치 (설정 시 기본값으로 사용)
    RAG_CURRENT_W_D: Optional[float] = None  # Current RRF Dense 가중치
    RAG_CURRENT_W_S: Optional[float] = None  # Current RRF Sparse 가중치
    RAG_ENHANCED_ALPHA: Optional[float] = 0.35  # Enhanced BM25 가중치 (Vector=1-alpha). 조밀 랜덤 서치 적용. None이면 내부 fallback

    @field_validator(
        "RAG_CURRENT_W_D",
        "RAG_CURRENT_W_S",
        "RAG_ENHANCED_ALPHA",
        "RAG_BM25_K1",
        "RAG_BM25_B",
        "RAG_LINEAR_QT_EXACT_W_BM25",
        "RAG_LINEAR_QT_EXACT_W_DENSE",
        "RAG_LINEAR_QT_EXACT_W_CONTRASTIVE",
        "RAG_LINEAR_QT_LONG_W_BM25",
        "RAG_LINEAR_QT_LONG_W_DENSE",
        "RAG_LINEAR_QT_LONG_W_CONTRASTIVE",
        mode="before",
    )
    @classmethod
    def optional_float(cls, v):
        return _optional_float(v)

    # Gating (RRF/linear 병합 점수 또는 리랭커 점수와 비교)
    # RRF 병합 시 top1은 보통 0.02~0.06 스케일. 0.25는 벡터 유사도용이라 RRF와 불일치 → 거의 항상 "근거 부족" 발생.
    # RRF 전용 경로: 0.02 이하로 설정. 리랭커 사용 시 점수 스케일이 다를 수 있으므로 .env에서 0.25 등으로 올려 사용 가능.
    RAG_GATING_TOP1_MIN_SCORE: float = 0.02  # top1 score 이하면 "근거 부족" (RRF 스케일 기준)
    RAG_GATING_MIN_EVIDENCE_COUNT: int = 2  # 최소 근거 개수

    # Rerank (HF Space API 전용. 로컬 Cross-Encoder 미사용)
    # 보수적 운영: RRF만 사용이 기본. Reranker 켤 때만 캐시·게이팅 필수.
    # 지연 완화: 1) RAG_RERANK_POOL_SIZE=10~15 로 줄이기 2) RAG_RERANK_GATING_ENABLE=True 유지(확신 높으면 스킵)
    #            3) RAG_USE_CROSS_ENCODER_RERANKER=False 로 끄고 RRF/메타 soft만 사용 4) RAG_RERANK_CACHE_ENABLE=True 로 캐시 활용
    # 모델: multifuly/certweb-reranker-model, 서빙 Space: multifuly/certweb-reranker
    RAG_RERANK_SCORES_PATH: Optional[str] = None  # rerank_scores.jsonl 경로 (레거시)
    RAG_USE_CROSS_ENCODER_RERANKER: bool = False  # True면 hybrid 후 Reranker API로 재정렬. 기본 False=RRF/채널 병합만 사용.
    RAG_RERANKER_MODEL_REPO_ID: str = "multifuly/certweb-reranker-model"  # Hub 모델 (참고용, 로컬 미로드)
    RAG_RERANKER_SPACE_REPO_ID: str = "multifuly/certweb-reranker"  # 서빙 Space (참고용)
    RAG_RERANKER_API_URL: str = ""  # 비우지 않으면 이 URL로 POST (query, passages) → scores. 기본값 없음(설정 필수)
    RAG_RERANKER_TIMEOUT: float = 90.0  # HF Space cold-start·네트워크 지연. .env RAG_RERANKER_TIMEOUT=120 등으로 상향 가능
    # HF Space 일시 500/502/429 시 재시도 횟수(추가 시도; 총 호출은 retries+1). 0이면 기존처럼 1회만.
    RAG_RERANKER_HTTP_RETRIES: int = 2
    RAG_RERANK_POOL_SIZE: int = 20  # RRF 상위 N개만 Cross-Encoder 입력. 20=지연/품질 균형. 10=지연 약 절반, 30=품질 우선 (env로 오버라이드)
    # Rerank gating: "확신 높은 질의"는 리랭커 생략해 지연 절감. 기본 ON.
    # - enable=true: top1 >= top1_min_score 이고 (top1-top2) >= min_gap 이면 reranker 생략
    # - RRF 점수 스케일이 작음(대략 0.01~0.05). top1_min_score=0.02, min_gap=0.002 는 .env에서 조정 가능
    RAG_RERANK_GATING_ENABLE: bool = True
    RAG_RERANK_GATING_TOP1_MIN_SCORE: float = 0.02
    RAG_RERANK_GATING_MIN_GAP: float = 0.002
    # 질의 타입·길이 기반 리랭커 게이팅: 쉬운/정형 쿼리는 리랭커 생략해 지연 절감
    # - RAG_RERANK_ALLOWED_QUERY_TYPES: 리랭커를 사용할 query_type 목록 (comma-separated)
    #   classify_query_type·rewrite 실패 시 fallback은 keyword|natural|mixed 만 반환.
    #   comparison·roadmap 등은 DB 벡터 query_type 라벨이 있을 때만 나오므로, 옛 목록을 두면
    #   fallback 경로에서 query_type이 허용 목록에 없어 리랭커가 스킵될 수 있음.
    # - RAG_RERANK_ALLOW_SHORT_KEYWORD: True면 짧은 키워드 쿼리(≤3단어)에도 리랭커 허용
    RAG_RERANK_ALLOWED_QUERY_TYPES: str = "keyword,natural,mixed"
    RAG_RERANK_ALLOW_SHORT_KEYWORD: bool = False
    # §2-9 추천 적합도: 재질의(리랭커 입력). 처음 질의 → 전공·목적·직무·취업용 등 보강 후 리랭커에 전달.
    RAG_RERANK_INPUT_ADD_CONTEXT: bool = True   # True=재질의 ON. 쿼리에 "전공: X 목적: Y 직무: Z 질의: ..." 추가 후 리랭커 호출.
    RAG_RERANK_INPUT_ADD_QUAL_NAME: bool = False  # True면 passage 앞에 "자격증: {qual_name}. " 추가. 학습이 "[자격증명:...]만"이었다면 False.
    RAG_RERANK_INPUT_ADD_QUERY_TYPE: bool = True  # True면 리랭커 쿼리 앞에 "쿼리유형: {query_type}" 추가. 리랭커가 자연어/키워드형 힌트 활용.
    RAG_INDEX_DIR: str = "data/rag_index"  # BM25 인덱스 등 디스크 저장 경로

    # BM25 검색과 벡터(HyDE 포함) 검색을 스레드로 병렬 실행 → p95 지연 완화 (PRF 사용 시 순차 유지)
    RAG_HYBRID_BM25_VECTOR_PARALLEL_ENABLE: bool = True

    # Hybrid Query Routing + Vector Gating (짧은 키워드 쿼리에서 Vector 오탐 억제)
    RAG_HYBRID_SHORT_W_BM25: float = 1.0   # 짧은 쿼리: BM25 가중치
    RAG_HYBRID_SHORT_W_VEC: float = 0.2    # 짧은 쿼리: Vector 가중치 (게이팅 통과 시)
    RAG_HYBRID_LONG_W_BM25: float = 0.30   # 긴 쿼리: BM25 가중치. 0.30 적용(지표 동일 유지)
    RAG_HYBRID_LONG_W_VEC: float = 1.0     # 긴 쿼리: Vector 가중치
    RAG_HYBRID_VEC_MIN_SCORE: float = 0.30  # Vector Top1 이하면 suspicious. 0.30=게이팅 추가 완화
    RAG_HYBRID_VEC_GAP_MIN: float = 0.002  # (Vec Top1 - Top2) < 이면 suspicious. 0.002=RRF Vector 반영 극대화
    RAG_HYBRID_BM25_TOP_FOR_GATING: int = 20  # Vec Top1이 BM25 이 순위 안에 없으면 suspicious
    RAG_HYBRID_DEBUG_LOG: bool = False     # True면 병합 시 로그 출력

    # HyDE (가상 문서 임베딩): 질의로 가상 답변 문서 생성 후 벡터 검색, 3-way RRF로 병합. 논문·방법론 확장.
    RAG_HYDE_ENABLE: bool = False  # 미적용(롤백). ablation 시 베이스라인 대비 상승했으나 운영에서 너프 판단으로 OFF.
    RAG_HYDE_WEIGHT: float = 0.2   # 3-way 시 HyDE 채널 가중치. BM25/Vector는 (1-RAG_HYDE_WEIGHT)/2 씩.
    RAG_HYDE_LONG_QUERY_ONLY: bool = True  # True면 4단어 초과 질의에만 HyDE 적용. 짧은 키워드 쿼리에서는 2-way 유지로 상위 순위 보존.
    RAG_HYDE_TEMPERATURE: float = 0.3  # HyDE 가상 문서 생성 시 LLM temperature. ablation 시 0.2/0.4 등 스윕.

    # COT(Chain-of-Thought) 쿼리 확장: 대안 검색 문구 2~3개 생성 후 다중 벡터 검색 RRF. 창의적 방법론.
    RAG_COT_QUERY_EXPANSION_ENABLE: bool = False  # True면 LLM 대안 질의 생성 후 vector 채널을 multi-query RRF로 확장
    RAG_COT_EXPANSION_MAX: int = 2   # COT 대안 질의 최대 개수 (실제 검색은 최대 이 수만큼 추가)
    # Step-back 메타 쿼리: 질의의 상위 목표(역할·커리어) 한 문장 추출 후 추가 벡터 검색, RRF 병합.
    RAG_STEPBACK_QUERY_ENABLE: bool = False  # True면 stepback 쿼리로 한 번 더 벡터 검색 후 기존 vector와 RRF

    # 후보 다양화·정렬 (다른 축 고도화)
    RAG_DEDUP_PER_CERT: bool = False  # True=자격증당 1개만 유지. 전체 골든 3모델 평가에서 Recall/MRR 악화로 False 유지
    RAG_QUERY_TYPE_WEIGHTS_ENABLE: bool = True  # True면 query_type별 BM25/Vector 가중치 (2-way·3-way 공통). 3-way 시 _three_way_weights_by_query_type 사용
    RAG_DOMAIN_AWARE_WEIGHTS_ENABLE: bool = True  # True면 IT·디지털 집중 신호가 약할 때 BM25 비중 상향(다도메인 자격증 공통). QUERY_TYPE과 함께 평가
    RAG_QUERY_TYPE_CONTRASTIVE_WEIGHTS_ENABLE: bool = True  # True면 3-way RRF 시 query_type별 Contrastive multiplier 적용. 스윕에서 지표 동일·지연 감소로 ON

    # Dense query rewrite (기본: vector 채널 중심)
    RAG_DENSE_USE_QUERY_REWRITE: bool = True
    RAG_DENSE_QUERY_REWRITE_FALLBACK: bool = True  # rewrite 실패 시 원본 query 사용
    # 채널 입력 contextual prompt (rank fusion 전):
    # - True면 vector/contrastive 입력을 "전공/목적/직무 + 질의" 형태로 보강
    # - BM25 적용은 별도 스위치(RAG_CHANNEL_CONTEXTUAL_PROMPT_APPLY_BM25)로 분리
    RAG_CHANNEL_CONTEXTUAL_PROMPT_ENABLE: bool = False
    RAG_CHANNEL_CONTEXTUAL_PROMPT_APPLY_BM25: bool = False

    # Dense 벡터: get_vector_search(..., use_rewrite=True)에서 원문+재작성 이중 RRF 적용 시점.
    # 하이브리드 메인(hybrid_retrieve)은 보통 use_rewrite=False + RAG_DENSE_MULTI_QUERY_ENABLE으로 원/재를 별도 병합.
    # - divergence(기본): 재작성≠원문이면 RRF(임베딩 배치 1회). 다도메인 자격증에 맞춤.
    # - legacy_non_it_only: IT·디지털 집중 신호 없을 때만 이중 검색(과거 “비IT” 게이트).
    # - off: 재작성 단일 검색만.
    RAG_DUAL_VECTOR_RRF_WHEN: str = "divergence"
    RAG_DENSE_SHORT_QUERY_BOOST: bool = True       # True=짧은 쿼리(5단어 이하) 시 보조 키워드 라인 추가(다른 방식 확장)
    RAG_DENSE_MEDIUM_QUERY_BOOST: bool = False     # True=6~9단어일 때 보조 키워드 한 줄 추가(평가 시 vector_only 하락으로 OFF 유지)
    RAG_DENSE_MULTI_QUERY_ENABLE: bool = True    # True=원본 쿼리+rewrite 각각 벡터 검색 후 linear fusion으로 병합
    RAG_DENSE_KEYWORD_EXPANSION_VECTOR_ENABLE: bool = True  # True=동의어/전공·직무 확장 쿼리로 3번째 벡터 검색 후 RRF 병합 (Recall@5 상승)
    RAG_REWRITE_ADD_QUERY_TYPE: bool = False  # True면 재질의 문자열 끝에 "쿼리유형: {query_type}" 추가 (벡터/contrastive 입력에도 포함). 기본 OFF.
    # Contextual child retrieval (실험): LLM이 생성한 chunk-specific context + chunk 임베딩 인덱스를
    # 별도 테이블(certificates_vectors_contextual)로 검색 후 parent 점수로 환원해 dense 채널에 결합.
    RAG_CONTEXTUAL_CHILD_ENABLE: bool = False
    RAG_CONTEXTUAL_CHILD_TOP_N: int = 90
    RAG_CONTEXTUAL_CHILD_BLEND_WEIGHT: float = 0.30
    RAG_CONTEXTUAL_CHILD_THRESHOLD: float = 0.0
    # Dense slot vector fallback: 도메인/난이도/희망직무/목적이 비거나 애매할 때 dense_slot_labels 유사도로 보정
    RAG_DENSE_SLOT_VECTOR_FALLBACK_ENABLE: bool = False  # True면 slot_vector_labels.lookup_slot_label_with_vector 사용
    RAG_DENSE_SLOT_VECTOR_MIN_SIM: float = 0.5   # 최소 유사도. 미만이면 보정하지 않음 (0.45~0.6 권장)
    # True면 구조화 재질의에서 값이 없음/미추론인 선택 필드 라인을 출력하지 않음(토큰·노이즈 감소). 대비 학습 데이터 생성 시 1 권장.
    RAG_DENSE_STRUCTURE_OMIT_EMPTY_LINES: bool = False
    # ----- BM25 (학습 없음: 인덱스 빌드 + 쿼리 확장 규칙 + k1/b 튜닝) -----
    # 개선 포인트:
    #  - 확장 규칙: app/rag/utils/query_processor.py 의 RECOMMENDATION_QUERY_MAP(직무/전공/목적→키워드), SYNONYM_DICT(동의어/약어) 보강
    #  - 도메인 매핑: data/domain_tokens.json(IT·비디지털 집중 토큰 등), domain_tokens_new_cert_full.json(넓은 직종 도메인·우선 사용). app/rag/utils/domain_tokens 에서 로드
    #  - 파라미터: RAG_BM25_K1, RAG_BM25_B 그리드서치. 인덱스/확장 변경 후 python -m app.rag index 재실행 필요
    # BM25 PRF (Pseudo-Relevance Feedback): 1차 검색 상위 문서에서 확장어 추출 후 2차 검색, RRF 병합.
    RAG_BM25_PRF_ENABLE: bool = False  # True면 BM25 2회(원본+확장) 후 RRF. 평가 시 3-way 악화로 미적용.
    RAG_BM25_PRF_TOP_K: int = 5   # 1차 상위 K개 문서에서 확장어 추출
    RAG_BM25_PRF_N_TERMS: int = 10  # 추출할 확장어 개수
    # 인덱스 빌드 시 적용. k1/b 변경 후 python -m app.rag index 재실행.
    RAG_BM25_K1: Optional[float] = None  # None=1.5. 논문/Elastic 권장 1.2~1.5
    RAG_BM25_B: Optional[float] = 0.5  # 0.5 적용(골든 Hit@4·nDCG 상승). None 시 과거 0.75
    RAG_BM25_USE_KOREAN_NGRAM: bool = True   # True=한글 2-gram 토크나이저
    RAG_BM25_NAME_BOOST: bool = True         # True=문서 앞에 자격명 2회 접두사 부스팅
    # 적용 기준: 전체 linear(3채널 fusion)에서 향상되면 적용. 평가: scripts/eval_bm25_options_bm25_vs_linear.py --short
    RAG_BM25_MULTI_EXPANSION_ENABLE: bool = False  # True=여러 확장 쿼리 BM25 RRF. 단일 BM25·과거 linear 평가에서 미적용 우수
    RAG_BM25_BASELINE_APPEND_ENABLE: bool = True   # 비 cert-centric 추천 질의에 베이스라인 용어 추가. 단일 BM25에서 개선
    RAG_BM25_MEDIUM_BASELINE_ENABLE: bool = False  # 4~7단어 비 cert-centric 시 직무·정보처리기사 추가. 단일 BM25에서 개선 없음

    # 멀티뷰 임베딩 (job/major/skill/recommendation view). False면 단일 뷰만 사용
    RAG_MULTIVIEW_ENABLE: bool = False

    # Metadata soft scoring (RRF 후보에 직무/전공 일치 가산, 분야 이탈 감점). 운영 기본 ON (full_challenger 경로).
    RAG_METADATA_SOFT_SCORE_ENABLE: bool = True
    RAG_METADATA_SOFT_JOB_BONUS: float = 0.25  # 직무 일치 가산 (옵션 비교 후 소폭 상향, 지표 동일·지연 개선)
    RAG_METADATA_SOFT_MAJOR_BONUS: float = 0.1493  # 전공 일치 가산(골든셋 균형점, random-search best)
    RAG_METADATA_SOFT_TARGET_BONUS: float = 0.16  # 목적 일치 가산
    RAG_METADATA_SOFT_DOMAIN_BONUS: float = 0.1514  # 도메인/정규화도메인 일치 가산(골든셋 균형점, random-search best)
    RAG_METADATA_SOFT_DOMAIN_KEYWORD_BONUS: float = 0.0522  # 도메인 키워드 일치 가산(골든셋 균형점, random-search best)
    RAG_METADATA_SOFT_FIELD_PENALTY: float = -0.20
    # True면 직무/관심 overlap·field_penalty용 qual 쪽 토큰에 qualification.main_field(단일 컬럼) 미포함.
    # NCS·main_fields 리스트·도메인 키워드는 그대로(인덱스 본문의 분야 문장과 별개).
    RAG_METADATA_SOFT_MAIN_FIELD_IN_JOB_MATCH: bool = True
    # 쿼리 도메인(IT·디지털 집중 vs 그 외 직종) ↔ 자격증 메타 도메인 불일치 시 감점
    RAG_METADATA_DOMAIN_MISMATCH_ENABLE: bool = True  # True면 도메인 불일치 시 감점 적용.
    RAG_METADATA_DOMAIN_MISMATCH_PENALTY: float = -0.3164  # 불일치 시 적용 감점(골든셋 균형점, random-search best)
    # 쿼리 도메인 슬롯이 분명한데 후보 자격증 도메인이 매칭 실패일 때 추가 감점(하드 드롭은 하지 않음).
    # 골든 20질의 A/B에서 -0.08은 Recall@5_qual/MRR_qual이 함께 악화되어, 기본은 기존과 동일 -0.15 유지.
    RAG_QUERY_OUT_OF_SCOPE_SOFT_PENALTY: float = -0.15
    # 프로필의 취득 자격증을 후보에서 완전 제외(hard filter). 골든/운영 정책에 맞게 끌 수 있음.
    RAG_ACQUIRED_CANDIDATE_HARD_EXCLUDE_ENABLE: bool = True

    # BM25 전용 개인화 (평가/챌린저용, production default OFF)
    RAG_BM25_PERSONALIZATION_ENABLED: bool = False
    RAG_BM25_PERSONALIZATION_MODE: str = "off"  # off | query_only | rerank_only | query_plus_rerank

    # 개인화 vector retrieval (프로필 있을 때만 적용, 없으면 기존 경로)
    RAG_PERSONALIZED_DENSE_REWRITE_ENABLE: bool = True   # True=재질의에 전공·학년·북마크·취득 자격증 반영(정확도 향상)
    RAG_PERSONALIZED_SOFT_SCORE_ENABLE: bool = False     # True면 RRF 후 개인화 soft score 적용
    RAG_PERSONALIZED_MAJOR_BONUS: float = 0.15
    RAG_PERSONALIZED_FAVORITE_FIELD_BONUS: float = 0.10
    RAG_PERSONALIZED_ACQUIRED_PENALTY: float = -1.0
    RAG_PERSONALIZED_NEXT_STEP_BONUS: float = 0.10
    RAG_PERSONALIZED_GRADE_DIFFICULTY_BONUS: float = 0.10
    RAG_PERSONALIZED_FAR_TOO_DIFFICULT_PENALTY: float = -0.15
    RAG_PERSONALIZED_FAR_TOO_EASY_PENALTY: float = -0.05

    # Contrastive retriever (768-dim 한국어 bi-encoder + FAISS. BM25 + dense1536 + contrastive768 3-way RRF)
    # Contrastive = 768-dim 한국어 전용 모델. 공식: Hub multifuly/cert-constrative-embedding (RAG_CONTRASTIVE_MODEL).
    # 기본값을 True로 두고, 필요 시 환경변수 RAG_CONTRASTIVE_ENABLE=0 으로 비활성화한다.
    RAG_CONTRASTIVE_ENABLE: bool = True  # True면 contrastive FAISS arm 추가, weighted RRF로 병합
    RAG_CONTRASTIVE_MODEL: str = ""  # Contrastive 전용 768-dim 모델. Hub: multifuly/cert-constrative-embedding. RAG_CONTRASTIVE_EMBEDDING_URL 있으면 무시
    RAG_CONTRASTIVE_EMBEDDING_URL: str = ""  # 비우지 않으면 질의 임베딩을 이 URL로 POST (HF Space 등). body: {"inputs": query}, 응답: [[float,...]] 768-dim
    RAG_CONTRASTIVE_EMBEDDING_TOKEN: str = ""  # HF Inference API 등 인증 시 Bearer 토큰 (선택)
    RAG_CONTRASTIVE_INDEX_DIR: str = "data/contrastive_index"  # cert_index.faiss, cert_metadata.json 위치 (정식 경로)
    # Contrastive arm 게이팅: 자연어·복합 목적 질의에만 Contrastive arm 사용해 비용·지연 절감
    # - RAG_CONTRASTIVE_ALLOWED_QUERY_TYPES: contrastive arm을 사용할 query_type 목록 (comma-separated)
    #   fallback query_type 은 keyword|natural|mixed 만. 짧은 키워드는 hybrid에서 별도로 contrastive 비활성.
    RAG_CONTRASTIVE_ALLOWED_QUERY_TYPES: str = "keyword,natural,mixed"
    RAG_RRF_W_BM25: float = 0.6
    RAG_RRF_W_DENSE1536: float = 0.55
    # 오프라인 골든 A/B(19_clean, retrieval-only)에서 0.92 대비 복합(2*R@5_qual+MRR_qual) 개선 → 1.05. 전체 골든 재검증 권장.
    RAG_RRF_W_CONTRASTIVE768: float = 1.05

    # 결과 다양화: MMR(Maximal Marginal Relevance) 기반 diversity ranking.
    # - 기본값: 비활성 (retrieval 지표 baseline 유지)
    # - RAG_MMR_ENABLE=True 시 최종 candidate에서 MMR을 적용해 유사한 자격증이 상위에 몰리는 것을 완화.
    # - RAG_MMR_LAMBDA: 0~1, relevance(λ) vs diversity(1-λ) 트레이드오프 (0.7 권장).
    RAG_MMR_ENABLE: bool = False
    RAG_MMR_LAMBDA: float = 0.7

    # hybrid 입력 질의 상한(바이트 폭주·DoS 완화). 0이면 잘라내지 않음.
    RAG_QUERY_MAX_CHARS: int = 12000

    # Pre-retrieval: 관측 trace / latency budget / 식별자 보수 경로 (opt_Pre-retrieval.md §2·§3 정합)
    RAG_PRE_RETRIEVAL_TRACE_ENABLE: bool = False  # True면 hybrid_retrieve가 JSON 한 줄 pre_retrieval_trace 로그
    # None이면 예산 게이트 비활성. 기본 15s로 확장 경로(HyDE 등)가 무한 대기하지 않게 함(운영에서 .env로 조정)
    RAG_PRE_RETRIEVAL_BUDGET_MS: Optional[int] = 15000
    # True이고 질의가 식별자·코드 위주로 판단되면 확장 경로 스킵 (dense_query_rewrite.query_suggests_identifier_heavy)
    # §2 식별자 보존: 식별자·코드 위주 질의에서는 확장(HyDE·MQ 등) 비용·드리프트를 줄이기 위해 기본 스킵
    RAG_SKIP_EXPANSION_ON_IDENTIFIER_HEAVY: bool = True
    # §2 규칙 4: 식별자·코드 위주 질의에서는 구조화 dense rewrite 생략(원문을 dense/BM25 타입 분류 입력으로 사용)
    RAG_SKIP_DENSE_REWRITE_ON_IDENTIFIER_HEAVY: bool = True
    # §2 규칙 7: RAG_PRE_RETRIEVAL_BUDGET_MS가 설정된 경우, 총 예산이 이 값(ms) 미만이면 dense rewrite를 생략(확장보다 먼저 비용 큰 단계 절감).
    # None이면 예산만으로는 rewrite를 끄지 않음. 예: 120 → 예산 100ms면 rewrite 스킵.
    RAG_PRE_RETRIEVAL_REWRITE_MIN_BUDGET_MS: Optional[int] = 120

    # hybrid_retrieve 결과 캐시(Redis): 리랭커·필터·프로필 없을 때만. opt_Pre-retrieval §16 경량 대응
    # Railway 등 Redis 연결 시 반복 질의 지연 감소(리랭커 미사용 경로).
    RAG_RETRIEVAL_RESULT_CACHE_ENABLE: bool = True
    RAG_RETRIEVAL_RESULT_CACHE_TTL_SECONDS: int = 300

    # Cache
    RAG_CACHE_TTL: int = 600  # Redis 캐시 TTL(초)
    
    # Reranker pair 캐싱 (API 호출 감소용)
    RAG_RERANK_CACHE_ENABLE: bool = True  # True면 (query, doc) pair 캐싱 활성화
    RAG_RERANK_CACHE_MAX_SIZE: int = 10000  # 최대 캐시 항목 수
    RAG_RERANK_CACHE_TTL: int = 3600  # pair 캐시 TTL(초)

    class Config:
        env_file = ".env"
        extra = "ignore"


_rag_field_overrides: ContextVar[Optional[Dict[str, Any]]] = ContextVar(
    "rag_field_overrides", default=None
)


@lru_cache()
def _rag_settings_from_env() -> RAGSettings:
    """환경·클래스 기본값만 로드. 랜덤 서치 등에서 clear_rag_settings_cache()로 갱신."""
    return RAGSettings()


def get_rag_settings() -> RAGSettings:
    """요청 단위 A/B 시 app.rag.experiment 미들웨어가 필드 오버라이드를 넣을 수 있음."""
    base = _rag_settings_from_env()
    ovr = _rag_field_overrides.get()
    if ovr:
        return base.model_copy(update=ovr)
    return base


def set_rag_field_overrides(overrides: Optional[Dict[str, Any]]) -> Token:
    """미들웨어에서만 사용. reset_rag_field_overrides(token)으로 복구."""
    return _rag_field_overrides.set(overrides)


def reset_rag_field_overrides(token: Token) -> None:
    _rag_field_overrides.reset(token)


def clear_rag_settings_cache() -> None:
    """환경변수 재로드·스크립트 trial 간 기본 설정 초기화."""
    _rag_settings_from_env.cache_clear()


def get_rag_index_dir() -> Path:
    s = get_rag_settings()
    p = Path(s.RAG_INDEX_DIR)
    p.mkdir(parents=True, exist_ok=True)
    return p
