from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime


# ---------------- Request Schemas ----------------
class RegisterRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=6)
    role: str = Field(default="user", pattern="^(admin|manager|user)$")
    department: Optional[str] = Field(default=None, pattern="^(Finance|HR|IT|Operations)$")
    experience_years: Optional[int] = Field(default=0, ge=0)
    location: Optional[str] = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class UpdateProfileRequest(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=50)
    department: Optional[str] = Field(default=None, pattern="^(Finance|HR|IT|Operations)$")
    experience_years: Optional[int] = Field(default=None, ge=0)
    location: Optional[str] = None


# ---------------- Response Schemas ----------------
class UserResponse(BaseModel):
    id: int
    name: str
    email: str
    role: str
    department: Optional[str]
    experience_years: Optional[int]
    location: Optional[str]
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"