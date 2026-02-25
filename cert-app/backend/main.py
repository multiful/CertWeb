
"""FastAPI main application."""
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from contextlib import asynccontextmanager
import logging
import time

from app.config import get_settings
from app.database import check_database_connection
from app.redis_client import redis_client
from app.api import certs, recommendations, admin, favorites, acquired_certs, jobs, auth, majors, ai_recommendations, fast_certs
from app.services.data_loader import data_loader

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

settings = get_settings()


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
    
    # Sync Cache to Redis if connected
    try:
        if redis_client.is_connected():
            logger.info("FLUSHING REDIS CACHE ON STARTUP to fix TypeErrors...")
            redis_client.flush_all()
            
            from app.services.fast_sync_service import FastSyncService
            from app.database import SessionLocal
            db = SessionLocal()
            try:
                FastSyncService.sync_all_to_redis(db)
            finally:
                db.close()
            logger.info("Initial Redis sync complete.")
        else:
            logger.warning("Redis not connected on startup. Skipping flush.")
    except Exception as e:
        logger.warning(f"Initial Redis setup failed: {e}")
    
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

# 3. Trusted Host (Safe but can stay)
from fastapi.middleware.trustedhost import TrustedHostMiddleware
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*"]
)

# 2. CORS
# Bearer 토큰 기반 인증은 CORS allow_credentials 불필요.
# allow_origins=["*"]로 Cloudflare/Vercel 프리뷰 URL 등 모든 환경에서 안정적으로 동작.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
)

# 1. Custom HTTP Middleware (Outermost for process time)
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    # Special handle for OPTIONS to be ABSOLUTELY sure no 400 occurs
    if request.method == "OPTIONS":
        return await call_next(request)
        
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    
    if hasattr(request.state, "rate_limit_remaining"):
        response.headers["X-RateLimit-Remaining"] = str(request.state.rate_limit_remaining)
    
    return response


# Exception handlers
@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    """Handle generic exceptions."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    # ServerErrorMiddleware가 이 핸들러를 호출할 때 CORSMiddleware를 우회하므로
    # 응답에 CORS 헤더를 직접 포함시켜야 한다.
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"},
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS, PATCH",
            "Access-Control-Allow-Headers": "*",
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
