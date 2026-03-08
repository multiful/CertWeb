"""RAG 하이퍼파라미터: top_k, alpha, thresholds, rerank 경로, 캐시 TTL 등."""
from functools import lru_cache
from pathlib import Path
from typing import Optional, Union

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
    RAG_TOP_N_CANDIDATES: int = 95  # RRF로 뽑을 후보 수 (Top95, 골든 평가에서 nDCG@20 소폭 상승으로 90→95 적용)
    RAG_RRF_K: int = 30  # RRF 상수. 30=골든 평가에서 R@20·Hit@20 최대. 논문(SIGIR'09) 표준은 60, 도메인별 튜닝 권장
    RAG_FUSION_METHOD: str = "linear"  # "rrf" | "linear". linear=min-max 정규화 후 λ*BM25+(1-λ)*Vector (골든 평가에서 R@20·Hit@20·MRR@4 상승으로 적용)
    RAG_VECTOR_TOP_N_OVERRIDE: Optional[int] = None  # 설정 시 벡터만 이 수만큼 뽑음. 100 실험 시 지표 동일·비용만 증가해 미적용
    RAG_ALPHA: float = 0.5  # hybrid: alpha*bm25_norm + (1-alpha)*vector_norm
    RAG_VECTOR_THRESHOLD: float = 0.025  # 유사도 임계값. 0.025 적용 시 rrf MRR@4 0.809→0.838 상승
    # 랜덤 서치로 찾은 최적 가중치 (설정 시 기본값으로 사용)
    RAG_CURRENT_W_D: Optional[float] = None  # Current RRF Dense 가중치
    RAG_CURRENT_W_S: Optional[float] = None  # Current RRF Sparse 가중치
    RAG_ENHANCED_ALPHA: Optional[float] = None  # Enhanced BM25 가중치 (Vector=1-alpha)

    @field_validator("RAG_CURRENT_W_D", "RAG_CURRENT_W_S", "RAG_ENHANCED_ALPHA", "RAG_BM25_K1", "RAG_BM25_B", mode="before")
    @classmethod
    def optional_float(cls, v):
        return _optional_float(v)

    # Gating
    RAG_GATING_TOP1_MIN_SCORE: float = 0.25  # top1 score 이하면 "근거 부족"
    RAG_GATING_MIN_EVIDENCE_COUNT: int = 2  # 최소 근거 개수

    # Rerank (오프라인 파일 / 경량 Cross-Encoder)
    RAG_RERANK_SCORES_PATH: Optional[str] = None  # rerank_scores.jsonl 경로
    RAG_USE_CROSS_ENCODER_RERANKER: bool = False  # True면 hybrid 후 경량 Cross-Encoder로 재정렬 (CPU 가능)
    RAG_CROSS_ENCODER_MODEL: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"  # CPU에서도 동작하는 소형 모델
    RAG_RERANK_POOL_SIZE: int = 30  # RRF 상위 N개만 Cross-Encoder 입력. 30=풀 확대(리랭커가 30개 안에서 top-4 선택). 10=지연 절반 (env로 오버라이드)
    # Rerank gating: "확신 높은 질의"는 리랭커 생략해 지연 절감. 기본 ON.
    # - enable=true: top1 >= top1_min_score 이고 (top1-top2) >= min_gap 이면 reranker 생략
    # - RRF 점수 스케일이 작음(대략 0.01~0.05). top1_min_score=0.02, min_gap=0.002 는 .env에서 조정 가능
    RAG_RERANK_GATING_ENABLE: bool = True
    RAG_RERANK_GATING_TOP1_MIN_SCORE: float = 0.02
    RAG_RERANK_GATING_MIN_GAP: float = 0.002
    # §2-9 추천 적합도: 리랭커 입력에 전공·목적·직무·자격증명 반영 (True=추천 문맥 확장, False=query+passage만)
    RAG_RERANK_INPUT_ADD_CONTEXT: bool = True   # 쿼리에 "전공: X, 목적: Y, 직무: Z, 질의: ..." 추가
    RAG_RERANK_INPUT_ADD_QUAL_NAME: bool = True  # passage 앞에 "자격증: {qual_name}. " 접두사
    RAG_INDEX_DIR: str = "data/rag_index"  # BM25 인덱스 등 디스크 저장 경로

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
    RAG_DEDUP_PER_CERT: bool = False  # True면 자격증(qual_id)당 최고점 청크 1개만 유지 후 재정렬 → 상위 목록이 서로 다른 자격증으로 다양해짐
    RAG_QUERY_TYPE_WEIGHTS_ENABLE: bool = False  # True면 query_type별 BM25/Vector 가중치 적용 (cert_name_included→BM25 강화, natural→Vector 강화)

    # Dense query rewrite (vector 채널만 적용, BM25/sparse 미적용)
    RAG_DENSE_USE_QUERY_REWRITE: bool = True
    RAG_DENSE_QUERY_REWRITE_FALLBACK: bool = True  # rewrite 실패 시 원본 query 사용
    RAG_DENSE_SHORT_QUERY_BOOST: bool = True       # True=짧은 쿼리(5단어 이하) 시 보조 키워드 라인 추가(다른 방식 확장)
    RAG_DENSE_MEDIUM_QUERY_BOOST: bool = False     # True=6~9단어일 때 보조 키워드 한 줄 추가(평가 시 vector_only 하락으로 OFF 유지)
    RAG_DENSE_MULTI_QUERY_ENABLE: bool = False    # True=원본 쿼리+rewrite 각각 벡터 검색 후 RRF로 병합(다양성·recall 향상, 논문 multi-query)
    # BM25 PRF (Pseudo-Relevance Feedback): 1차 검색 상위 문서에서 확장어 추출 후 2차 검색, RRF 병합. 방법론 확장.
    RAG_BM25_PRF_ENABLE: bool = False  # True면 BM25 2회(원본+확장) 후 RRF로 하나의 BM25 리스트로 사용
    RAG_BM25_PRF_TOP_K: int = 5   # 1차 상위 K개 문서에서 확장어 추출
    RAG_BM25_PRF_N_TERMS: int = 10  # 추출할 확장어 개수

    # BM25 파라미터 (인덱스 빌드 시 적용. 변경 후 python -m app.rag index 재실행 필요)
    RAG_BM25_K1: Optional[float] = None  # None=1.5. 논문/Elastic 권장 1.2~1.5
    RAG_BM25_B: Optional[float] = 0.5  # 0.5 적용(골든 평가 Hit@4·nDCG@20·nDCG@4 상승). None/미설정 시 과거 0.75.
    RAG_BM25_USE_KOREAN_NGRAM: bool = True   # True=한글 2-gram 토크나이저, False=공백 기준만
    RAG_BM25_NAME_BOOST: bool = True         # True=문서 앞에 자격명 2회 접두사 부스팅
    RAG_BM25_MULTI_EXPANSION_ENABLE: bool = False  # True=여러 확장 쿼리로 BM25 검색 후 RRF 병합 (PRF와 별개)
    # BM25 다른 방식 확장: n-gram 매칭 외에 추천 질의에 베이스라인 용어 무조건 추가 (RECOMMENDATION_QUERY_MAP과 별개)
    RAG_BM25_BASELINE_APPEND_ENABLE: bool = True   # True=비 cert-centric 추천 질의에 베이스라인 용어 추가
    RAG_BM25_MEDIUM_BASELINE_ENABLE: bool = True  # True=4~7단어 비 cert-centric일 때 직무·정보처리기사 추가(평가 후 적용 유지)

    # 멀티뷰 임베딩 (job/major/skill/recommendation view). False면 단일 뷰만 사용
    RAG_MULTIVIEW_ENABLE: bool = False

    # Metadata soft scoring (RRF 후보에 직무/전공 일치 가산, 분야 이탈 감점). 운영 기본 ON (full_challenger 경로).
    RAG_METADATA_SOFT_SCORE_ENABLE: bool = True
    RAG_METADATA_SOFT_JOB_BONUS: float = 0.22  # 직무 일치 가산 강화(RRF 순위 상승)
    RAG_METADATA_SOFT_MAJOR_BONUS: float = 0.14  # 전공 일치 가산 (목적과 동일 수준)
    RAG_METADATA_SOFT_TARGET_BONUS: float = 0.14  # 목적 일치 가산 상향(RRF 품질)
    RAG_METADATA_SOFT_FIELD_PENALTY: float = -0.20

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

    # Cache
    RAG_CACHE_TTL: int = 600  # Redis 캐시 TTL(초)
    
    # Reranker pair 캐싱 (API 호출 감소용)
    RAG_RERANK_CACHE_ENABLE: bool = True  # True면 (query, doc) pair 캐싱 활성화
    RAG_RERANK_CACHE_MAX_SIZE: int = 10000  # 최대 캐시 항목 수
    RAG_RERANK_CACHE_TTL: int = 3600  # pair 캐시 TTL(초)

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache()
def get_rag_settings() -> RAGSettings:
    return RAGSettings()


def get_rag_index_dir() -> Path:
    s = get_rag_settings()
    p = Path(s.RAG_INDEX_DIR)
    p.mkdir(parents=True, exist_ok=True)
    return p
