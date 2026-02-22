from fastapi import Header, HTTPException, Depends
from jose import jwt, JWTError
import logging
from app.config import get_settings

logger = logging.getLogger(__name__)

import requests

def get_current_user_from_token(authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authentication required")
    
    token = authorization.split(" ")[1]
    settings = get_settings()
    
    try:
        # Validate the token directly via Supabase Auth API
        res = requests.get(
            f"{settings.SUPABASE_URL}/auth/v1/user",
            headers={"Authorization": f"Bearer {token}", "apikey": settings.SUPABASE_ANON_KEY},
            timeout=5
        )
        if res.status_code != 200:
            raise HTTPException(status_code=401, detail="Invalid or expired token")
        
        user_data = res.json()
        payload = {"sub": user_data.get("id"), "email": user_data.get("email"), **user_data}
        return payload
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token validation error via Supabase API: {e}")
        raise HTTPException(status_code=401, detail="Authentication failed")

