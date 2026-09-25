from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.config import settings
from app.models import User, UserRole
from app.schemas.auth import (
    PasswordChangeRequest,
    RefreshRequest,
    Token,
    UserCreate,
    UserResponse,
    UserUpdate,
)
from app.utils.exceptions import AppException
from app.utils.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_password_hash,
    verify_password,
)

router = APIRouter()


@router.post('/login', response_model=Token, summary='Login and get access/refresh tokens')
async def login(
    db: Annotated[AsyncSession, Depends(get_db)],
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    response: Response,
) -> Token:
    result = await db.execute(select(User).where(User.email == form_data.username))
    user = result.scalar_one_or_none()

    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Incorrect email or password',
            headers={'WWW-Authenticate': 'Bearer'},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='User account is disabled',
        )

    access_token = create_access_token(sub=user.id, email=user.email, role=user.role.value)
    refresh_token = create_refresh_token(sub=user.id)

    # Set refresh token as HttpOnly cookie
    response.set_cookie(
        key='refresh_token',
        value=refresh_token,
        httponly=True,
        secure=settings.ENVIRONMENT == 'production',
        samesite='lax',
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
    )

    user.last_login = datetime.utcnow()
    await db.commit()

    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post('/refresh', response_model=Token, summary='Refresh access token')
async def refresh_token(
    db: Annotated[AsyncSession, Depends(get_db)],
    request: RefreshRequest,
    response: Response,
) -> Token:
    try:
        payload = decode_token(request.refresh_token)
        if payload.type != 'refresh':
            raise AppException('INVALID_TOKEN', 'Invalid token type', status_code=401)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Invalid or expired refresh token',
        )

    result = await db.execute(select(User).where(User.id == payload.sub))
    user = result.scalar_one_or_none()

    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='User not found or inactive',
        )

    access_token = create_access_token(sub=user.id, email=user.email, role=user.role.value)
    new_refresh_token = create_refresh_token(sub=user.id)

    response.set_cookie(
        key='refresh_token',
        value=new_refresh_token,
        httponly=True,
        secure=settings.ENVIRONMENT == 'production',
        samesite='lax',
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
    )

    return Token(
        access_token=access_token,
        refresh_token=new_refresh_token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post('/logout', summary='Logout and clear refresh token')
async def logout(response: Response) -> dict:
    response.delete_cookie(
        key='refresh_token',
        httponly=True,
        secure=settings.ENVIRONMENT == 'production',
        samesite='lax',
    )
    return {'message': 'Successfully logged out'}


@router.get('/me', response_model=UserResponse, summary='Get current user profile')
async def get_current_user_profile(
    current_user: Annotated[User, Depends(get_current_user)],
) -> UserResponse:
    return UserResponse.model_validate(current_user)


@router.post(
    '/register',
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary='Register new user (admin only)',
)
async def register(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    user_data: UserCreate,
) -> UserResponse:
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Only administrators can create users',
        )

    result = await db.execute(select(User).where(User.email == user_data.email))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Email already registered',
        )

    user = User(
        email=user_data.email,
        hashed_password=get_password_hash(user_data.password),
        full_name=user_data.full_name,
        role=UserRole(user_data.role),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    return UserResponse.model_validate(user)


@router.patch('/me/password', summary='Change current user password')
async def change_password(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    password_data: PasswordChangeRequest,
) -> dict:
    if not verify_password(password_data.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Current password is incorrect',
        )

    current_user.hashed_password = get_password_hash(password_data.new_password)
    await db.commit()

    return {'message': 'Password changed successfully'}


@router.get('/users', response_model=list[UserResponse], summary='List all users (admin only)')
async def list_users(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    skip: int = 0,
    limit: int = 100,
) -> list[UserResponse]:
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Only administrators can list users',
        )

    result = await db.execute(select(User).offset(skip).limit(limit))
    users = result.scalars().all()
    return [UserResponse.model_validate(u) for u in users]


@router.patch('/users/{user_id}', response_model=UserResponse, summary='Update user (admin only)')
async def update_user(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    user_id: UUID,
    user_data: UserUpdate,
) -> UserResponse:
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Only administrators can update users',
        )

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='User not found',
        )

    update_data = user_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(user, field, value)

    await db.commit()
    await db.refresh(user)

    return UserResponse.model_validate(user)
