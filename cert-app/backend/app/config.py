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
    
    # Security
    JOB_SECRET: str = "change-this-in-production"
    
    # Supabase (Optional)
    SUPABASE_URL: str = ""
    SUPABASE_ANON_KEY: str = ""
    SUPABASE_SERVICE_ROLE_KEY: str = ""
    SUPABASE_JWT_SECRET: str = ""
    
    # AI (OpenAI)
    OPENAI_API_KEY: str = ""
    
    # Cache TTL (seconds)
    CACHE_TTL_LIST: int = 300  # 5 minutes
    CACHE_TTL_DETAIL: int = 1800  # 30 minutes
    CACHE_TTL_STATS: int = 3600  # 1 hour
    CACHE_TTL_RECOMMENDATIONS: int = 600  # 10 minutes
    
    # Rate Limiting
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_WINDOW: int = 60  # seconds
    
    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
