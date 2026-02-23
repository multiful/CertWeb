"""API dependencies."""
from fastapi import Depends, HTTPException, status, Request, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import Optional
from functools import lru_cache
import logging

from app.database import get_db
from app.config import get_settings
from app.redis_client import redis_client

settings = get_settings()
logger = logging.getLogger(__name__)
security = HTTPBearer(auto_error=False)


def get_db_session(db: Session = Depends(get_db)) -> Session:
    """Get database session."""
    return db


def verify_job_secret(x_job_secret: Optional[str] = Header(None)) -> bool:
    """Verify job secret for admin endpoints."""
    if not x_job_secret:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-Job-Secret header"
        )
    
    if x_job_secret != settings.JOB_SECRET:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid job secret"
        )
    
    return True


def check_rate_limit(request: Request) -> None:
    """Check rate limit for request."""
    # Get client IP
    client_ip = request.headers.get("X-Forwarded-For", request.client.host)
    if client_ip and "," in client_ip:
        client_ip = client_ip.split(",")[0].strip()
    
    key = f"rate_limit:{client_ip}"
    
    allowed, remaining, reset_after = redis_client.check_rate_limit(
        key,
        settings.RATE_LIMIT_REQUESTS,
        settings.RATE_LIMIT_WINDOW
    )
    
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded",
            headers={
                "X-RateLimit-Limit": str(settings.RATE_LIMIT_REQUESTS),
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": str(reset_after),
                "Retry-After": str(reset_after)
            }
        )
    
    # Add rate limit headers to response
    request.state.rate_limit_remaining = remaining


import base64
from jose import jwt, JWTError
from app.models import Profile

import httpx
from jose import jwk

@lru_cache(maxsize=1)
def _get_supabase_jwks(url: str) -> dict:
    """Fetch and cache Supabase JWKS."""
    try:
        response = httpx.get(url, timeout=5)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Failed to fetch JWKS from {url}: {e}")
        return {}

def _decode_supabase_token(token: str) -> dict:
    """Helper to decode Supabase JWT token supporting HS256 (user/service) and RS256/ES256 (access tokens)."""
    try:
        # Check header to determine algorithm
        header = jwt.get_unverified_header(token)
        alg = header.get("alg")
        
        if alg == "HS256":
            # Symmetric key verification (classic Supabase)
            secret = settings.SUPABASE_JWT_SECRET
            if len(secret) > 20 and '=' in secret:
                try:
                    decoded_secret = base64.b64decode(secret)
                except:
                    decoded_secret = secret
            else:
                decoded_secret = secret
                
            return jwt.decode(
                token, 
                decoded_secret, 
                algorithms=["HS256"], 
                options={"verify_aud": False}
            )
            
        elif alg in ["RS256", "ES256"]:
            # Asymmetric key verification (modern Supabase / Gotrue)
            if not settings.SUPABASE_URL:
                 logger.warning("SUPABASE_URL not set, cannot fetch JWKS for RS256/ES256 token")
                 raise Exception("SUPABASE_URL required for RS256/ES256 verification")
                 
            jwks_url = f"{settings.SUPABASE_URL}/auth/v1/.well-known/jwks.json"
            try:
                # Add User-Agent to avoid blocking by some servers
                jwks = _get_supabase_jwks(jwks_url)
            except Exception as e:
                logger.error(f"JWKS fetch failed: {e}")
                raise Exception("JWKS fetch failed")

            if not jwks or "keys" not in jwks:
                raise Exception("Empty or invalid JWKS response")
            
            # Find matching key
            kid = header.get("kid")
            key_data = None
            
            for k in jwks.get("keys", []):
                if k.get("kid") == kid:
                    key_data = k
                    break
            
            if not key_data:
                # Fallback: try first key with matching alg if no kid match
                for k in jwks.get("keys", []):
                    if k.get("alg") == alg:
                        key_data = k
                        break
                
            if key_data:
                try:
                    key = jwk.construct(key_data)
                    return jwt.decode(
                        token,
                        key,
                        algorithms=[alg],
                        options={"verify_aud": False}
                    )
                except Exception as e:
                     raise Exception(f"Token signature verification failed: {e}")
            else:
                raise Exception(f"No matching key found in JWKS for alg={alg} kid={kid}")
        
        else:
            raise Exception(f"Unsupported algorithm: {alg}")
            
    except Exception as e:
        logger.error(f"Token decode error: {e}")
        raise e

def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db_session)
) -> Optional[str]:
    """Get optional user ID from JWT token."""
    if not credentials:
        return None
    
    try:
        payload = _decode_supabase_token(credentials.credentials)
        uuid_sub = payload.get("sub")
        if not uuid_sub:
            return None
            
        profile = db.query(Profile).filter(Profile.id == uuid_sub).first()
        if profile and profile.userid:
            return profile.userid
        return uuid_sub
    except Exception:
        return None

def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db_session)
) -> str:
    """Get current user ID (readable userid) from JWT token (required)."""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication token",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    try:
        payload = _decode_supabase_token(credentials.credentials)
        uuid_sub = payload.get("sub")
        if not uuid_sub:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload: missing sub"
            )
            
        # Ensure profile exists (Social Login Support)
        profile = db.query(Profile).filter(Profile.id == uuid_sub).first()
        if not profile:
            # Create a shell profile from JWT data
            email = payload.get("email")
            # For social logins, we might have full_name or name in metadata
            meta = payload.get("user_metadata", {})
            name = meta.get("full_name") or meta.get("name")
            
            try:
                profile = Profile(
                    id=uuid_sub,
                    email=email,
                    name=name,
                    nickname=name or email.split("@")[0] if email else "New User",
                    userid=None # Let them set it later
                )
                db.add(profile)
                db.commit()
                db.refresh(profile)
                logger.info(f"Auto-created profile for social user: {uuid_sub}")
            except Exception as e:
                db.rollback()
                logger.warning(f"Failed to auto-create profile: {e}")
        
        if profile and profile.userid:
            return profile.userid
            
        return uuid_sub # Fallback to UUID if profile.userid is not yet set
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"JWT validation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"}
        )
