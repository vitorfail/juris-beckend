from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from jose import JWTError, jwt
from pydantic import BaseModel
from .config import settings
from .database import get_db
from . import models

security = HTTPBearer()

class TokenData(BaseModel):
    user_id: str
    law_firm_id: str
    email: str
    role: str

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> models.User:
    """
    Obtém o usuário atual baseado no token JWT de forma assíncrona.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Não foi possível validar as credenciais",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        token = credentials.credentials
        payload = jwt.decode(
            token, 
            settings.SECRET_KEY, 
            algorithms=[settings.ALGORITHM]
        )
        user_id: str = payload.get("sub")
        email: str = payload.get("email")
        law_firm_id: str = payload.get("law_firm_id")
        role: str = payload.get("role")
        
        if user_id is None or email is None:
            raise credentials_exception
            
        token_data = TokenData(
            user_id=user_id,
            email=email,
            law_firm_id=law_firm_id,
            role=role
        )
    except JWTError:
        raise credentials_exception
    
    # Query assíncrona usando select()
    query = select(models.User).filter(
        models.User.id == token_data.user_id,
        models.User.is_active == True
    )
    result = await db.execute(query)
    user = result.scalar_one_or_none()
    
    if user is None:
        raise credentials_exception
    
    return user

async def get_current_active_user(
    current_user: models.User = Depends(get_current_user)
) -> models.User:
    """
    Verifica se o usuário está ativo.
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Usuário inativo"
        )
    return current_user

async def get_current_admin_user(
    current_user: models.User = Depends(get_current_active_user)
) -> models.User:
    """
    Verifica se o usuário é admin.
    """
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permissão insuficiente"
        )
    return current_user

async def get_current_lawyer_user(
    current_user: models.User = Depends(get_current_active_user)
) -> models.User:
    """
    Verifica se o usuário é advogado ou admin.
    """
    if current_user.role not in ["admin", "lawyer"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas advogados ou administradores podem acessar"
        )
    return current_user

def get_law_firm_filter(
    current_user: models.User = Depends(get_current_active_user)
) -> dict:
    """
    Retorna filtro para consultas baseadas no escritório do usuário.
    """
    return {"law_firm_id": current_user.law_firm_id}