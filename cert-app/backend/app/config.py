"""Application configuration."""
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings."""
    
    # Project
    PROJECT_NAME: str = "Certification API"
    DEBUG: bool = False
    API_V1_PREFIX: str = "/api/v1"
    
    # Database
    DATABASE_URL: str = "postgresql://postgres:password@localhost:5432/certdb"
    
    # Redis. REDIS_SOCKET_TIMEOUT: 단일 명령/파이프라인 타임아웃(초). bulk sync 시 2초는 부족할 수 있음
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_SOCKET_TIMEOUT: int = 10
    
    # Security (빈값이면 main.py startup 시 경고; .env에서 설정 필수)
    JOB_SECRET: str = ""
    
    # Supabase (Optional)
    SUPABASE_URL: str = ""
    SUPABASE_ANON_KEY: str = ""
    SUPABASE_SERVICE_ROLE_KEY: str = ""
    SUPABASE_JWT_SECRET: str = ""
    # Supabase 벡터 intent 라벨 테이블 사용 여부 및 임계값
    INTENT_LABEL_LOOKUP_ENABLE: bool = False
    INTENT_LABEL_MIN_SIMILARITY: float = 0.75
    
    # AI (OpenAI). OPENAI_TIMEOUT: 임베딩/채팅 API 호출 타임아웃(초). 미설정 시 60
    OPENAI_API_KEY: str = ""
    OPENAI_TIMEOUT: float = 60.0
    # metadata emb_model_version / 재색인 drift 추적용. 기본 text-embedding-3-small (1536차원)
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"
    
    # Cache TTL (seconds)
    CACHE_TTL_LIST: int = 600  # 10 minutes
    CACHE_TTL_DETAIL: int = 3600  # 1 hour
    CACHE_TTL_STATS: int = 3600  # 1 hour
    CACHE_TTL_RECOMMENDATIONS: int = 600  # 10 minutes
    CACHE_TTL_RAG: int = 600  # RAG /search/rag, /rag/ask 응답 캐시 (10분)

    # Rate Limiting
    RATE_LIMIT_REQUESTS: int = 200
    RATE_LIMIT_WINDOW: int = 60  # seconds
    AUTH_RATE_LIMIT_REQUESTS: int = 5  # Auth 전용: 분당 횟수 (send_code, login 등)
    AUTH_RATE_LIMIT_WINDOW: int = 60  # seconds

    # CORS (쉼표 구분. 비어 있으면 기본값 사용)
    CORS_ORIGINS: str = ""
    # Trusted Host (쉼표 구분. 비어 있으면 Render + localhost)
    ALLOWED_HOSTS: str = ""

    # RAG: 유사도 임계값 (이하면 결과에서 제외). 0이면 미적용.
    # 3-way RAG 기본값.
    RAG_MATCH_THRESHOLD: float = 0.4
    # RAG /search/rag: content 컬럼 조회 여부. False=egress 절감(보수적 기본). True=롤백용.
    RAG_SEARCH_INCLUDE_CONTENT: bool = False

    # 프로덕션 RAG A/B (Railway). False면 challenger=코드·.env 기본만, 미들웨어 오버라이드 없음.
    RAG_AB_ENABLE: bool = False
    # 0=전원 control, 100=전원 challenger. 50이면 약 절반 트래픽이 challenger(기본 튜닝).
    RAG_AB_CHALLENGER_PCT: int = 0
    # True면 X-RAG-Variant: control|challenger 헤더가 분할보다 우선(스테이징·디버그).
    RAG_AB_ALLOW_HEADER_OVERRIDE: bool = False

    # 에러 트래킹 (비어 있으면 Sentry 비활성)
    SENTRY_DSN: str = ""
    SENTRY_ENVIRONMENT: str = "production"

    # 문의 수신 이메일 (contact API)
    CONTACT_EMAIL: str = ""

    # Email (SMTP)
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    EMAIL_USER: str = ""
    EMAIL_PASSWORD: str = ""
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
