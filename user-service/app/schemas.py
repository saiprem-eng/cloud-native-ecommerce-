"""
Pydantic schemas for User Service request/response models.
"""

from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime
from enum import Enum


class UserRole(str, Enum):
    ADMIN = "admin"
    CUSTOMER = "customer"
    VENDOR = "vendor"


class UserStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    PENDING = "pending"


# ─────────────────────────── Auth Schemas ───────────────────────────

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, description="Min 8 chars, requires uppercase, lowercase, number, symbol")
    first_name: str = Field(..., min_length=1, max_length=50)
    last_name: str = Field(..., min_length=1, max_length=50)
    phone_number: Optional[str] = Field(None, pattern=r"^\+[1-9]\d{1,14}$")
    role: UserRole = UserRole.CUSTOMER

    class Config:
        json_schema_extra = {
            "example": {
                "email": "john.doe@example.com",
                "password": "SecurePass@123",
                "first_name": "John",
                "last_name": "Doe",
                "phone_number": "+14155552671",
                "role": "customer"
            }
        }


class LoginRequest(BaseModel):
    email: EmailStr
    password: str

    class Config:
        json_schema_extra = {
            "example": {
                "email": "john.doe@example.com",
                "password": "SecurePass@123"
            }
        }


class ConfirmRegistrationRequest(BaseModel):
    email: EmailStr
    confirmation_code: str = Field(..., min_length=6, max_length=6)


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    email: EmailStr
    confirmation_code: str
    new_password: str = Field(..., min_length=8)


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    access_token: str


# ─────────────────────────── User Schemas ───────────────────────────

class UserBase(BaseModel):
    email: EmailStr
    first_name: str
    last_name: str
    phone_number: Optional[str] = None
    role: UserRole = UserRole.CUSTOMER


class UserCreate(UserBase):
    password: str


class UserUpdate(BaseModel):
    first_name: Optional[str] = Field(None, min_length=1, max_length=50)
    last_name: Optional[str] = Field(None, min_length=1, max_length=50)
    phone_number: Optional[str] = None


class UserResponse(UserBase):
    user_id: str
    status: UserStatus
    email_verified: bool
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    class Config:
        from_attributes = True


# ─────────────────────────── Auth Responses ───────────────────────────

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    id_token: str
    token_type: str = "Bearer"
    expires_in: int


class MessageResponse(BaseModel):
    message: str
    success: bool = True
