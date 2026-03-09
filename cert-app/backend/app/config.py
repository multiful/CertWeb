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
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # Security (빈값이면 main.py startup 시 경고; .env에서 설정 필수)
    JOB_SECRET: str = ""
    
    # Supabase (Optional)
    SUPABASE_URL: str = ""
    SUPABASE_ANON_KEY: str = ""
    SUPABASE_SERVICE_ROLE_KEY: str = ""
    SUPABASE_JWT_SECRET: str = ""
    
    # AI (OpenAI)
    OPENAI_API_KEY: str = ""
    
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
    # 선정 근거: docs/RAG_고도화_총정리.md §2-2 참고.
    RAG_MATCH_THRESHOLD: float = 0.4
    # RAG /search/rag: content 컬럼 조회 여부. False=egress 절감(보수적 기본). True=롤백용. docs/PERFORMANCE_IMPROVEMENT_METRICS.md
    RAG_SEARCH_INCLUDE_CONTENT: bool = False

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
