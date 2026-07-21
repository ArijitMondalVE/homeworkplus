"""
Pydantic v2 schemas for authentication endpoints.
"""
from uuid import UUID
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    email: EmailStr
    username: str = Field(min_length=3, max_length=30, pattern=r"^[a-zA-Z0-9_]+$")
    full_name: str = Field(min_length=2, max_length=100)
    password: str = Field(min_length=8, max_length=128)
    grade_level: str | None = None
    preferred_language: str | None = "en"


class LoginRequest(BaseModel):
    username: str
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class UserResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: UUID
    email: str
    username: str
    full_name: str
    avatar_url: str | None = None
    grade_level: str | None = None
    preferred_language: str = "en"
    xp_points: int = 0
    level: int = 1
    streak_days: int = 0
    total_questions_solved: int = 0
    is_active: bool = True
    is_premium: bool = False
    role: str = "student"
    created_at: datetime


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserResponse
