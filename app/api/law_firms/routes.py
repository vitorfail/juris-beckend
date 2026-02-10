from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from ...database import get_db
from ... import schemas, models
from ...dependencies import get_current_active_user, get_current_admin_user

router = APIRouter()

@router.get("/", response_model=List[schemas.LawFirmInDB])
def read_law_firms(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_admin_user)
):
    """Listar todos os escritórios (apenas admin)."""
    law_firms = db.query(models.LawFirm).offset(skip).limit(limit).all()
    return law_firms

@router.get("/{law_firm_id}", response_model=schemas.LawFirmInDB)
def read_law_firm(
    law_firm_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Obter um escritório específico."""
    law_firm = db.query(models.LawFirm).filter(models.LawFirm.id == law_firm_id).first()
    if not law_firm:
        raise HTTPException(status_code=404, detail="Escritório não encontrado")
    return law_firm

@router.post("/criar_firma", response_model=schemas.LawFirmInDB, status_code=status.HTTP_201_CREATED)
def create_law_firm(
    law_firm: schemas.LawFirmCreate,
    db: Session = Depends(get_db)
):
    """Criar novo escritório (apenas admin)."""
    # Verificar se CNPJ já existe
    if law_firm.cnpj:
        existing = db.query(models.LawFirm).filter(models.LawFirm.cnpj == law_firm.cnpj).first()
        if existing:
            raise HTTPException(status_code=400, detail="CNPJ já cadastrado")
    
    db_law_firm = models.LawFirm(**law_firm.model_dump())
    db.add(db_law_firm)
    db.commit()
    db.refresh(db_law_firm)
    return db_law_firm
