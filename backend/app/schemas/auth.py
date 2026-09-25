from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: Literal['bearer'] = 'bearer'
    expires_in: int


class TokenPayload(BaseModel):
    sub: UUID
    email: EmailStr
    role: str
    exp: int
    type: Literal['access', 'refresh']


class UserBase(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=1, max_length=255)
    role: Literal['pharmacist', 'manager', 'admin'] = 'pharmacist'


class UserCreate(UserBase):
    password: str = Field(min_length=8, max_length=128)

    @field_validator('password')
    @classmethod
    def validate_password(cls, v: str) -> str:
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        return v


class UserUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=1, max_length=255)
    role: Literal['pharmacist', 'manager', 'admin'] | None = None
    is_active: bool | None = None


class UserInDB(UserBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    is_active: bool
    last_login: datetime | None
    created_at: datetime
    updated_at: datetime


class UserResponse(UserInDB):
    pass


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8, max_length=128)

    @field_validator('new_password')
    @classmethod
    def validate_password(cls, v: str) -> str:
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        return v
