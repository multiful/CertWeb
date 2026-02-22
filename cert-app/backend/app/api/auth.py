from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
import requests
import logging
from typing import Optional

from app.database import get_db
from app.config import get_settings
from app.utils.auth import get_current_user_from_token
from app.schemas.auth import (
    EmailRequest,
    EmailVerifyCodeRequest,
    AuthSignupComplete,
    AuthSignupResponse,
    AuthLoginRequest,
    AuthTokenResponse,
    UserIdCheckRequest,
    UserProfileUpdate
)

router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()
logger = logging.getLogger(__name__)

def _admin_headers():
    return {
        "apikey": settings.SUPABASE_SERVICE_ROLE_KEY,
        "Authorization": f"Bearer {settings.SUPABASE_SERVICE_ROLE_KEY}",
        "Content-Type": "application/json"
    }

def _admin_get_user_by_email(email: str):
    try:
        res = requests.get(
            f"{settings.SUPABASE_URL}/auth/v1/admin/users",
            headers=_admin_headers(),
            timeout=10
        )
        if res.status_code >= 400:
            return None
        users = res.json().get("users", [])
        for u in users:
            if u.get("email") == email:
                return u
    except Exception:
        pass
    return None

def _admin_delete_user(user_id: str):
    try:
        requests.delete(
            f"{settings.SUPABASE_URL}/auth/v1/admin/users/{user_id}",
            headers=_admin_headers(),
            timeout=10
        )
    except Exception:
        pass

@router.post("/email/send-code")
async def send_email_code(payload: EmailRequest, db: Session = Depends(get_db)):
    """[Sign-up Step 1] Send OTP to email."""
    # Check if email already exists in our DB
    row = db.execute(
        text("SELECT 1 FROM profiles WHERE email = :email"),
        {"email": payload.email}
    ).scalar()
    if row:
        raise HTTPException(status_code=400, detail="이미 가입된 이메일입니다.")

    try:
        # Supabase OTP
        res = requests.post(
            f"{settings.SUPABASE_URL}/auth/v1/otp",
            headers={"apikey": settings.SUPABASE_ANON_KEY, "Content-Type": "application/json"},
            json={"email": payload.email, "create_user": True},
            timeout=10
        )
        if res.status_code >= 400:
            logger.error(f"Supabase OTP error: {res.text}")
            raise HTTPException(status_code=400, detail="인증 코드 발송 실패")
    except Exception as e:
        logger.error(f"OTP send error: {e}")
        raise HTTPException(status_code=502, detail="인증 메일 발송 중 오류가 발생했습니다.")

    return {"message": "인증 코드가 발송되었습니다."}

@router.post("/email/verify-code")
async def verify_email_code(payload: EmailVerifyCodeRequest):
    """[Sign-up Step 2] Verify OTP code."""
    try:
        res = requests.post(
            f"{settings.SUPABASE_URL}/auth/v1/verify",
            headers={"apikey": settings.SUPABASE_ANON_KEY, "Content-Type": "application/json"},
            json={
                "type": "email",
                "email": payload.email,
                "token": payload.code
            },
            timeout=10
        )
        if res.status_code >= 400:
            raise HTTPException(status_code=400, detail="인증 코드가 올바르지 않거나 만료되었습니다.")
    except Exception:
        raise HTTPException(status_code=502, detail="인증 확인 중 오류가 발생했습니다.")

    return {"success": True, "message": "이메일 인증이 완료되었습니다."}

@router.post("/check-userid")
async def check_userid(payload: UserIdCheckRequest, db: Session = Depends(get_db)):
    """Check if userid is already taken."""
    id_row = db.execute(
        text("SELECT 1 FROM profiles WHERE userid = :uid"),
        {"uid": payload.userid}
    ).scalar()
    
    if id_row:
        return {"available": False, "message": "이미 사용 중인 아이디입니다."}
    return {"available": True, "message": "사용 가능한 아이디입니다."}

@router.post("/signup-complete", response_model=AuthSignupResponse, status_code=201)
async def signup_complete(
    payload: AuthSignupComplete, 
    db: Session = Depends(get_db),
    token_payload: dict = Depends(get_current_user_from_token)
):
    """[Sign-up Step 3] Complete registration and save profile."""
    # Security Check: Ensure the token belongs to the email being registered
    token_email = token_payload.get("email") or token_payload.get("user_metadata", {}).get("email")
    if token_email != payload.email:
        raise HTTPException(status_code=403, detail="토큰의 이메일과 요청된 이메일이 일치하지 않습니다.")

    if payload.password != payload.password_confirm:
        raise HTTPException(status_code=400, detail="비밀번호가 일치하지 않습니다.")

    # Check userid uniqueness
    id_row = db.execute(
        text("SELECT 1 FROM profiles WHERE userid = :uid"),
        {"uid": payload.userid}
    ).scalar()
    if id_row:
        raise HTTPException(status_code=400, detail="이미 사용 중인 아이디입니다.")

    user_id = None
    is_new_user = False

    # Check if user already exists in Supabase (from Step 1/2)
    target = _admin_get_user_by_email(payload.email)

    try:
        if target:
            user_id = target["id"]
            # Update password and metadata via Admin API
            up_res = requests.put(
                f"{settings.SUPABASE_URL}/auth/v1/admin/users/{user_id}",
                headers=_admin_headers(),
                json={
                    "password": payload.password,
                    "email_confirm": True,
                    "user_metadata": {
                        "name": payload.name,
                        "full_name": payload.name,
                        "userid": payload.userid,
                        "nickname": payload.userid,
                        "birth_date": payload.birth_date,
                        "detail_major": payload.detail_major
                    }
                },
                timeout=10
            )
            if up_res.status_code >= 400:
                raise HTTPException(status_code=400, detail=f"Supabase 업데이트 실패: {up_res.text}")
        else:
            # Create user via Admin API
            create_res = requests.post(
                f"{settings.SUPABASE_URL}/auth/v1/admin/users",
                headers=_admin_headers(),
                json={
                    "email": payload.email,
                    "password": payload.password,
                    "email_confirm": True,
                    "user_metadata": {
                        "name": payload.name,
                        "full_name": payload.name,
                        "userid": payload.userid,
                        "nickname": payload.userid,
                        "birth_date": payload.birth_date,
                        "detail_major": payload.detail_major
                    }
                },
                timeout=10
            )
            if create_res.status_code >= 400:
                raise HTTPException(status_code=400, detail=f"Supabase 생성 실패: {create_res.text}")
            
            data = create_res.json()
            user_id = data.get("id") or data.get("user", {}).get("id")
            is_new_user = True

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Supabase signup integration error: {e}")
        raise HTTPException(status_code=502, detail="Supabase 연동 중 오류가 발생했습니다.")

    if not user_id:
        raise HTTPException(status_code=500, detail="사용자 ID 확보 실패")

    # Save to local database
    params = {
        "id": user_id,
        "name": payload.name,
        "userid": payload.userid,
        "nickname": payload.userid, # Default to userid
        "birth_date": payload.birth_date,
        "email": payload.email,
        "detail_major": payload.detail_major
    }

    try:
        if payload.detail_major:
            # Ensure major exists in major table for foreign key constraint
            db.execute(
                text("INSERT INTO major (major_name) VALUES (:major) ON CONFLICT (major_name) DO NOTHING"),
                {"major": payload.detail_major}
            )

        db.execute(
            text("""
                INSERT INTO profiles (id, name, userid, nickname, birth_date, email, detail_major)
                VALUES (:id, :name, :userid, :nickname, :birth_date, :email, :detail_major)
                ON CONFLICT (id) DO UPDATE SET
                    name = EXCLUDED.name,
                    userid = EXCLUDED.userid,
                    nickname = EXCLUDED.nickname,
                    birth_date = EXCLUDED.birth_date,
                    email = EXCLUDED.email,
                    detail_major = EXCLUDED.detail_major
            """),
            params
        )
        db.commit()
    except Exception as e:
        db.rollback()
        if is_new_user:
            _admin_delete_user(user_id)
        logger.error(f"Profile creation error: {e}")
        raise HTTPException(status_code=500, detail="프로필 생성 중 오류가 발생했습니다.")

    return AuthSignupResponse(
        user_id=str(user_id),
        email=payload.email,
        message="회원가입이 완료되었습니다. 이제 로그인하세요."
    )

@router.post("/login", response_model=AuthTokenResponse)
async def login(payload: AuthLoginRequest, db: Session = Depends(get_db)):
    """Login with userid and password."""
    # 1) Get email from local DB
    row = db.execute(
        text("SELECT email FROM profiles WHERE userid = :uid"),
        {"uid": payload.userid}
    ).mappings().first()

    if not row:
        raise HTTPException(status_code=400, detail="존재하지 않는 아이디입니다.")

    email = row["email"]

    # 2) Authenticate with Supabase
    try:
        res = requests.post(
            f"{settings.SUPABASE_URL}/auth/v1/token?grant_type=password",
            headers={
                "apikey": settings.SUPABASE_ANON_KEY,
                "Content-Type": "application/json",
            },
            json={"email": email, "password": payload.password},
            timeout=10,
        )
        data = res.json()
    except Exception:
        raise HTTPException(status_code=502, detail="로그인 요청 실패")

    if res.status_code >= 400:
        err_msg = data.get("msg") or data.get("error_description") or "로그인에 실패했습니다."
        raise HTTPException(status_code=400, detail=err_msg)

    user_id = data.get("user", {}).get("id")

    # 3) Ensure profile exists (fallback)
    try:
        db.execute(
            text("""
                INSERT INTO profiles (id, email)
                VALUES (:id, :email)
                ON CONFLICT (id) DO NOTHING
            """),
            {"id": user_id, "email": email}
        )
        db.commit()
    except Exception:
        db.rollback()

    return AuthTokenResponse(
        access_token=data.get("access_token"),
        refresh_token=data.get("refresh_token"),
        user_id=user_id,
        expires_in=data.get("expires_in")
    )

@router.patch("/profile")
async def update_profile(
    payload: UserProfileUpdate,
    db: Session = Depends(get_db),
    token_payload: dict = Depends(get_current_user_from_token)
):
    """Update user profile (name, userid, major)."""
    user_id = token_payload.get("sub")
    
    # 1. Prepare updates
    updates = {}
    if payload.name: 
        updates["name"] = payload.name
        updates["full_name"] = payload.name
    if payload.nickname:
        updates["nickname"] = payload.nickname
    if payload.userid: 
        # Usually userid is not changed after signup, but if allowed:
        existing = db.execute(
            text("SELECT id FROM profiles WHERE userid = :uid AND id != :id"),
            {"uid": payload.userid, "id": user_id}
        ).scalar()
        if existing:
            raise HTTPException(status_code=400, detail="이미 사용 중인 아이디입니다.")
        updates["userid"] = payload.userid
    if payload.detail_major: 
        updates["detail_major"] = payload.detail_major
        # Ensure major exists
        db.execute(
            text("INSERT INTO major (major_name) VALUES (:major) ON CONFLICT (major_name) DO NOTHING"),
            {"major": payload.detail_major}
        )

    if not updates:
        return {"message": "변경 사항이 없습니다."}

    # 2. Update local DB
    local_fields = ["name", "nickname", "userid", "detail_major"]
    local_updates = {k: v for k, v in updates.items() if k in local_fields}
    
    if local_updates:
        set_clause = ", ".join([f"{k} = :{k}" for k in local_updates.keys()])
        db.execute(
            text(f"UPDATE profiles SET {set_clause}, updated_at = NOW() WHERE id = :id"),
            {**local_updates, "id": user_id}
        )
    
    # 3. Update Supabase metadata
    try:
        requests.put(
            f"{settings.SUPABASE_URL}/auth/v1/admin/users/{user_id}",
            headers=_admin_headers(),
            json={"user_metadata": updates},
            timeout=10
        )
    except Exception as e:
        logger.warning(f"Failed to sync metadata to Supabase: {e}")

    db.commit()
    return {"message": "프로필이 업데이트되었습니다.", "updates": updates}
