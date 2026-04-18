from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import timedelta
from typing import Any

from app.database import get_db
from app.core import security
from app.dependencies import get_current_active_user
from app.models import User
from app.auth import UserLogin, TokenResponse, TokenRefreshResponse
from app.config import settings

router = APIRouter()

@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Login de usuário",
    description="Autentica um usuário e retorna token JWT com informações do escritório"
)
async def login(
    *,
    db: AsyncSession = Depends(get_db),
    user_data: UserLogin,
    request: Request
) -> Any:
    """
    Realiza o login do usuário e retorna um token JWT de forma assíncrona.
    """
    # Buscar usuário pelo email usando select() assíncrono
    query = select(User).filter(User.email == user_data.email)
    result = await db.execute(query)
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou senha incorretos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Verificar senha
    if not security.verify_password(user_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou senha incorretos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Verificar se usuário está ativo
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuário inativo. Contate o administrador.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Criar token de acesso
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        data={
            "sub": str(user.id),
            "law_firm_id": str(user.law_firm_id),
            "email": user.email,
            "name": user.name,
            "role": user.role
        },
        expires_delta=access_token_expires
    )
    
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user_id=user.id,
        law_firm_id=user.law_firm_id,
        email=user.email,
        name=user.name,
        role=user.role,
        is_active=user.is_active
    )

@router.post(
    "/login/form",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Login com form OAuth2",
    description="Endpoint de login compatível com OAuth2 Password Flow (para Swagger UI)"
)
async def login_with_form(
    db: AsyncSession = Depends(get_db),
    form_data: OAuth2PasswordRequestForm = Depends()
) -> Any:
    """
    Endpoint de login compatível com OAuth2 Password Flow (Assíncrono).
    """
    query = select(User).filter(User.email == form_data.username)
    result = await db.execute(query)
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou senha incorretos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Verificar senha
    if not security.verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou senha incorretos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuário inativo",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        data={
            "sub": str(user.id),
            "law_firm_id": str(user.law_firm_id),
            "email": user.email,
            "name": user.name,
            "role": user.role
        },
        expires_delta=access_token_expires
    )
    
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user_id=user.id,
        law_firm_id=user.law_firm_id,
        email=user.email,
        name=user.name,
        role=user.role,
        is_active=user.is_active
    )

@router.post(
    "/refresh",
    response_model=TokenRefreshResponse,
    summary="Renovar token",
    description="Gera um novo token de acesso usando o token atual válido"
)
async def refresh_token(
    current_user: User = Depends(get_current_active_user)
) -> Any:
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        data={
            "sub": str(current_user.id),
            "law_firm_id": str(current_user.law_firm_id),
            "email": current_user.email,
            "name": current_user.name,
            "role": current_user.role
        },
        expires_delta=access_token_expires
    )
    
    return TokenRefreshResponse(
        access_token=access_token,
        token_type="bearer"
    )

@router.post(
    "/logout",
    status_code=status.HTTP_200_OK,
    summary="Logout"
)
async def logout() -> dict:
    return {
        "message": "Logout realizado com sucesso",
        "detail": "Token descartado no lado do cliente."
    }

@router.get(
    "/me",
    response_model=UserLogin,
    summary="Usuário atual"
)
async def get_current_user_info(
    current_user: User = Depends(get_current_active_user)
) -> Any:
    return current_user

@router.post(
    "/verify-token",
    status_code=status.HTTP_200_OK,
    summary="Verificar token"
)
async def verify_token(
    current_user: User = Depends(get_current_active_user)
) -> dict:
    return {
        "valid": True,
        "user_id": str(current_user.id),
        "law_firm_id": str(current_user.law_firm_id),
        "email": current_user.email,
        "role": current_user.role
    }