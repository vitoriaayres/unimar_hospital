from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Literal
from uuid import UUID

from jose import jwt
from passlib.context import CryptContext

from app.config import settings

pwd_context = CryptContext(
    schemes=['bcrypt'], deprecated='auto', bcrypt__rounds=settings.BCRYPT_ROUNDS
)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(
    sub: UUID,
    email: str,
    role: str,
    expires_delta: timedelta | None = None,
) -> str:
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode = {
        'sub': str(sub),
        'email': email,
        'role': role,
        'exp': expire,
        'iat': datetime.utcnow(),
        'type': 'access',
    }
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_refresh_token(sub: UUID, expires_delta: timedelta | None = None) -> str:
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    to_encode = {
        'sub': str(sub),
        'exp': expire,
        'iat': datetime.utcnow(),
        'type': 'refresh',
    }
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token(token: str) -> TokenPayload:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return TokenPayload(**payload)
    except jwt.ExpiredSignatureError:
        raise ValueError('Token has expired')
    except jwt.JWTError as e:
        raise ValueError(f'Invalid token: {e}')


class TokenPayload:
    def __init__(
        self,
        sub: str,
        email: str | None = None,
        role: str | None = None,
        exp: int = 0,
        iat: int = 0,
        type: Literal['access', 'refresh'] = 'access',
        **kwargs: Any,
    ):
        self.sub = UUID(sub)
        self.email = email
        self.role = role
        self.exp = exp
        self.iat = iat
        self.type = type

    @classmethod
    def model_validate(cls, payload: dict) -> TokenPayload:
        return cls(
            sub=payload['sub'],
            email=payload.get('email'),
            role=payload.get('role'),
            exp=payload.get('exp', 0),
            type=payload.get('type', 'access'),
        )
