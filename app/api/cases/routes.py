from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from ...database import get_db
from ... import schemas, models
from ...dependencies import get_current_active_user

router = APIRouter()

@router.post("/", response_model=schemas.CaseInDB, status_code=status.HTTP_201_CREATED)
def create_case(
    case: schemas.CaseCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Criar novo processo."""
    # Verificar se cliente pertence ao escritório
    client = db.query(models.Client).filter(
        models.Client.id == case.client_id,
        models.Client.law_firm_id == current_user.law_firm_id
    ).first()
    
    if not client:
        raise HTTPException(status_code=400, detail="Cliente não encontrado")
    
    db_case = models.Case(
        law_firm_id=current_user.law_firm_id,
        **case.model_dump()
    )
    db.add(db_case)
    db.commit()
    db.refresh(db_case)
    return db_case

@router.get("/", response_model=List[schemas.CaseInDB])
def read_cases(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Listar processos do escritório."""
    cases = db.query(models.Case).filter(
        models.Case.law_firm_id == current_user.law_firm_id
    ).offset(skip).limit(limit).all()
    return cases