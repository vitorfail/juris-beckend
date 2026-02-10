from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from ...database import get_db
from ... import schemas, models
from ...dependencies import get_current_active_user, get_current_admin_user
from ...core.security import get_password_hash

router = APIRouter()

@router.post("/register", response_model=schemas.UserInDB, status_code=status.HTTP_201_CREATED)
def register_user(
    user: schemas.UserCreate,
    db: Session = Depends(get_db)
):
    """Registrar novo usuário."""
    # Verificar se email já existe
    existing = db.query(models.User).filter(models.User.email == user.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email já registrado")
    
    # Verificar se law_firm existe
    law_firm = db.query(models.LawFirm).filter(models.LawFirm.id == user.law_firm_id).first()
    if not law_firm:
        raise HTTPException(status_code=400, detail="Escritório não encontrado")
    
    db_user = models.User(
        law_firm_id=user.law_firm_id,
        name=user.name,
        email=user.email,
        password_hash=get_password_hash(user.password),
        role=user.role,
        is_active=user.is_active
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

@router.get("/me", response_model=schemas.UserInDB)
def read_current_user(
    current_user: models.User = Depends(get_current_active_user)
):
    """Obter informações do usuário atual."""
    return current_user

@router.get("/", response_model=List[schemas.UserInDB])
def read_users(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_admin_user)
):
    """Listar todos os usuários (apenas admin)."""
    users = db.query(models.User).filter(
        models.User.law_firm_id == current_user.law_firm_id
    ).offset(skip).limit(limit).all()
    return users