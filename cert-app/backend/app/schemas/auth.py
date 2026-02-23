from pydantic import BaseModel, Field, EmailStr
from typing import Optional

class EmailRequest(BaseModel):
    email: EmailStr

class EmailVerifyCodeRequest(BaseModel):
    email: EmailStr
    code: str

class UserIdCheckRequest(BaseModel):
    userid: str

class AuthSignupComplete(BaseModel):
    name: str = Field(..., min_length=1)
    userid: str = Field(..., min_length=4, max_length=20, pattern=r"^[a-zA-Z0-9_]+$")
    email: EmailStr
    password: str = Field(..., min_length=6)
    password_confirm: str = Field(..., min_length=6)
    birth_date: str = Field(..., description="YYMMDD")
    detail_major: Optional[str] = None

class UserProfileUpdate(BaseModel):
    name: Optional[str] = None
    userid: Optional[str] = None
    nickname: Optional[str] = None
    detail_major: Optional[str] = None
    grade_year: Optional[int] = None

class AuthSignupResponse(BaseModel):
    user_id: str
    email: str
    message: str

class AuthLoginRequest(BaseModel):
    userid: str
    password: str

class AuthTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    refresh_token: Optional[str] = None
    user_id: str
    expires_in: Optional[int] = None

class UserIdCheckResponse(BaseModel):
    available: bool

class EmailCheckResponse(BaseModel):
    available: bool
    message: str
