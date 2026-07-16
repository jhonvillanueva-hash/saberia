from datetime import datetime
from uuid import UUID
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    """Request schema for user registration."""
    email: EmailStr
    password: str = Field(..., min_length=8)
    display_name: str = Field(..., min_length=1, max_length=150)


class LoginRequest(BaseModel):
    """Request schema for login."""
    email: EmailStr
    password: str


class GoogleLoginRequest(BaseModel):
    """Request schema for Google login."""
    id_token: str


class TokenResponse(BaseModel):
    """Response schema for token endpoints."""
    access_token: str
    token_type: str = "bearer"


class UserProfile(BaseModel):
    """Response schema for user profile."""
    id: UUID
    email: EmailStr
    display_name: str
    avatar_url: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True