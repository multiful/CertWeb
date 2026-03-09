
"""FastAPI main application."""
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from contextlib import asynccontextmanager
import asyncio
import logging
import time

from app.config import get_settings
from app.database import check_database_connection
from app.redis_client import redis_client
from app.logging_config import log_audit
from app.api import certs, recommendations, admin, favorites, acquired_certs, jobs, auth, majors, ai_recommendations, fast_certs
from app.rag.api import rag_router
from app.services.data_loader import data_loader

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

settings = get_settings()

# Sentry (optional)
if settings.SENTRY_DSN and settings.SENTRY_DSN.strip():
    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        sentry_sdk.init(
            dsn=settings.SENTRY_DSN.strip(),
            environment=settings.SENTRY_ENVIRONMENT or "production",
            integrations=[FastApiIntegration()],
            traces_sample_rate=0.1,
            send_default_pii=False,
        )
        logger.info("Sentry error tracking enabled")
    except Exception as e:
        logger.warning("Sentry init failed: %s", e)

# CORS 허용 오리진 (환경변수 없으면 기본값: Vercel 프로덕션 + 샌드 + DEBUG 시 localhost)
def _get_allowed_origins() -> list[str]:
    if settings.CORS_ORIGINS and settings.CORS_ORIGINS.strip():
        return [o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()]
    base = [ "https://cert-web-multifuls-projects.vercel.app", "https://cert-web-sand.vercel.app", ]
    if settings.DEBUG:
        base.extend(["http://localhost:5173", "http://127.0.0.1:5173"])
    return base

# Trusted Host 허용 호스트 (환경변수 없으면 Render + localhost)
def _get_allowed_hosts() -> list[str]:
    if settings.ALLOWED_HOSTS and settings.ALLOWED_HOSTS.strip():
        return [h.strip() for h in settings.ALLOWED_HOSTS.split(",") if h.strip()]
    return ["certweb-xzpx.onrender.com", "localhost", "127.0.0.1"]

ALLOWED_ORIGINS = _get_allowed_origins()
ALLOWED_HOSTS = _get_allowed_hosts()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    logger.info("Starting up...")
    
    if not (settings.JOB_SECRET or settings.JOB_SECRET.strip()):
        logger.warning(
            "JOB_SECRET is not set. Set JOB_SECRET in .env for production. "
            "Admin API (X-Job-Secret) will reject requests until configured."
        )

    # SMTP 설정 상태 체크 (Render 배포 시 환경변수 누락 조기 감지)
    if settings.EMAIL_USER and settings.EMAIL_PASSWORD:
        logger.info(
            "SMTP configured: host=%s port=%d user=%s",
            settings.SMTP_HOST, settings.SMTP_PORT, settings.EMAIL_USER,
        )
    else:
        logger.warning(
            "SMTP NOT configured (EMAIL_USER/EMAIL_PASSWORD missing). "
            "Contact form emails will NOT be sent. "
            "Add SMTP env vars in Render Dashboard > Environment."
        )
    
    # # Load CSV Data
    # try:
    #     data_loader.load_data()
    #     logger.info("CSV Data loaded successfully.")
    # except Exception as e:
    #     logger.error(f"Failed to load CSV data: {e}")

    # Check database connection
    if check_database_connection():
        logger.info("Database connection: OK")
    else:
        logger.warning("Database connection: FAILED")
    
    # Redis sync은 백그라운드로 실행 — yield 이전에 블로킹하면 Render 헬스체크 타임아웃으로 배포 실패
    async def _background_redis_sync():
        await asyncio.sleep(5)  # 서버 준비 후 시작
        try:
            if not redis_client.is_connected():
                logger.warning("Redis not connected. Skipping background sync.")
                return
            logger.info("Background Redis sync starting...")
            redis_client.flush_all()
            from app.services.fast_sync_service import FastSyncService
            from app.database import SessionLocal
            loop = asyncio.get_running_loop()
            db = SessionLocal()
            try:
                await loop.run_in_executor(None, FastSyncService.sync_all_to_redis, db)
            finally:
                db.close()
            logger.info("Background Redis sync complete.")
        except Exception as e:
            logger.warning("Background Redis sync failed: %s", e)

    asyncio.create_task(_background_redis_sync())

    yield
    
    # Shutdown
    logger.info("Shutting down...")


# Create FastAPI app
app = FastAPI(
    title=settings.PROJECT_NAME,
    description="""
    Certification Query and Recommendation API
    
    ## Features
    
    * **Certifications**: Search, filter, and browse certifications
    * **Statistics**: View year/round statistics for certifications
    * **Recommendations**: Get certification recommendations based on major/field
    * **Favorites**: Save and manage favorite certifications (requires auth)
    
    ## Authentication
    
    Favorites API requires Bearer token authentication.
    Other endpoints are publicly accessible with rate limiting.
    
    ## Admin Endpoints
    
    Admin endpoints require `X-Job-Secret` header for automation tasks.
    """,
    version="1.0.0",
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    openapi_url="/openapi.json" if settings.DEBUG else None,
    lifespan=lifespan,
)

# ============== Middleware Order (Last added is first to run) ==============

# 4. GZip compression (Innermost)
from fastapi.middleware.gzip import GZipMiddleware
app.add_middleware(
    GZipMiddleware,
    minimum_size=1000
)

# 3. Trusted Host (실제 서비스 도메인만 허용)
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=ALLOWED_HOSTS,
)

# 2. CORS (프론트 도메인만 허용)
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
)

# 1. Custom HTTP Middleware (Outermost: process time + 보안 헤더)
@app.middleware("http")
async def add_process_time_and_security_headers(request: Request, call_next):
    # OPTIONS(preflight)는 TrustedHost 검사 전에 여기서 처리. Host가 프록시/스캐너로 인해
    # 허용 목록에 없을 수 있어 CORS만 적용하고 200 반환.
    if request.method == "OPTIONS":
        origin = (request.headers.get("origin") or "").strip()
        allow_origin = origin if origin and origin in ALLOWED_ORIGINS else (ALLOWED_ORIGINS[0] if ALLOWED_ORIGINS else "*")
        return Response(
            status_code=status.HTTP_200_OK,
            headers={
                "Access-Control-Allow-Origin": allow_origin,
                "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS, PATCH",
                "Access-Control-Allow-Headers": "*",
                "Access-Control-Max-Age": "86400",
            },
        )
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)

    # HTTP 캐시: 읽기 전용·거의 안 변하는 GET에만 TTL 기반 Cache-Control (egress/재요청 감소)
    if request.method == "GET" and response.status_code == 200:
        path = (getattr(request, "url", None) and getattr(request.url, "path", None)) or request.scope.get("path") or ""
        path = (path or "").rstrip("/")
        prefix = (settings.API_V1_PREFIX or "/api/v1").rstrip("/")
        if path.startswith(prefix):
            rest = path[len(prefix) :].lstrip("/")
            if rest == "certs":
                response.headers["Cache-Control"] = f"public, max-age={settings.CACHE_TTL_LIST}"
            elif rest.startswith("certs/filter-options"):
                response.headers["Cache-Control"] = f"public, max-age={settings.CACHE_TTL_LIST}"
            elif "/stats" in rest or "/trends" in rest:
                response.headers["Cache-Control"] = f"public, max-age={settings.CACHE_TTL_STATS}"
            elif rest.startswith("certs/") and "/" not in rest.replace("certs/", "", 1):
                response.headers["Cache-Control"] = f"public, max-age={settings.CACHE_TTL_DETAIL}"
            elif rest == "jobs":
                response.headers["Cache-Control"] = "public, max-age=3600"
            elif rest.startswith("jobs/") and "/" not in rest.replace("jobs/", "", 1):
                response.headers["Cache-Control"] = "public, max-age=3600"
            elif "recommendations/majors" in rest or "recommendations/popular-majors" in rest:
                response.headers["Cache-Control"] = f"public, max-age={settings.CACHE_TTL_LIST}"
    if hasattr(request.state, "rate_limit_remaining"):
        response.headers["X-RateLimit-Remaining"] = str(request.state.rate_limit_remaining)
    # 보안 헤더
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    if request.url.scheme == "https":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    client_ip = request.headers.get("X-Forwarded-For") or (getattr(request.client, "host", None) if request.client else None)
    if client_ip and "," in str(client_ip):
        client_ip = str(client_ip).split(",")[0].strip()
    log_audit(
        method=request.method,
        path=request.url.path or "",
        status_code=response.status_code,
        duration_ms=process_time * 1000,
        user_id=None,
        client_ip=client_ip or "",
    )
    return response


# Exception handlers
@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    """Handle generic exceptions. 로그에는 스택만, 파라미터/토큰 원문은 남기지 않음."""
    logger.exception("Unhandled exception: %s", type(exc).__name__)
    origin = request.headers.get("origin") or ""
    allow_origin = origin if origin in ALLOWED_ORIGINS else (ALLOWED_ORIGINS[0] if ALLOWED_ORIGINS else "*")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"},
        headers={
            "Access-Control-Allow-Origin": allow_origin,
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS, PATCH",
            "Access-Control-Allow-Headers": "*",
            "X-Frame-Options": "DENY",
            "X-Content-Type-Options": "nosniff",
        },
    )


# ============== Routes ==============

# API v1 routes
v1_prefix = settings.API_V1_PREFIX

app.include_router(certs.router, prefix=v1_prefix)
app.include_router(recommendations.router, prefix=v1_prefix)
app.include_router(admin.router, prefix=v1_prefix)
app.include_router(favorites.router, prefix=v1_prefix)
app.include_router(acquired_certs.router, prefix=v1_prefix)
app.include_router(jobs.router, prefix=v1_prefix)
app.include_router(auth.router, prefix=v1_prefix)
app.include_router(majors.router, prefix=v1_prefix)
app.include_router(ai_recommendations.router, prefix=v1_prefix)
app.include_router(fast_certs.router, prefix=v1_prefix)
app.include_router(rag_router, prefix=v1_prefix)
from app.api import contact
app.include_router(contact.router, prefix=v1_prefix)


# ============== Health Check ==============

@app.get("/health", tags=["health"])
@app.head("/health")
async def health_check():
    """Health check endpoint."""
    db_status = "healthy" if check_database_connection() else "unhealthy"
    redis_status = "healthy" if redis_client.is_connected() else "unhealthy"
    
    overall_status = "healthy" if db_status == "healthy" else "degraded"
    
    return {
        "status": overall_status,
        "database": db_status,
        "redis": redis_status,
        "version": "1.0.0"
    }


@app.get("/", tags=["root"])
async def root():
    """Root endpoint."""
    return {
        "name": settings.PROJECT_NAME,
        "version": "1.0.0",
        "docs": "/docs" if settings.DEBUG else None,
        "health": "/health"
    }


# ============== Main ==============

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level="info"
    )
