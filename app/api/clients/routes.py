from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from ...database import get_db
from ... import schemas, models
from ...dependencies import get_current_active_user
from sqlalchemy import not_

router = APIRouter()



@router.post("/", response_model=schemas.ClientInDB, status_code=status.HTTP_201_CREATED)
def create_client(
    client: schemas.ClientCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Criar novo cliente."""
    # Verificar se documento já existe no mesmo escritório
    if client.document:
        existing = db.query(models.Client).filter(
            models.Client.law_firm_id == current_user.law_firm_id,
            models.Client.document == client.document
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail="Documento já cadastrado")
    
    db_client = models.Client(
        law_firm_id=current_user.law_firm_id,
        **client.model_dump()
    )
    db.add(db_client)
    db.commit()
    db.refresh(db_client)
    return db_client

@router.get("/", response_model=List[schemas.ClientInDB])
def read_clients(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Listar clientes do escritório."""
    clients = db.query(models.Client).filter(
        models.Client.law_firm_id == current_user.law_firm_id
    ).offset(skip).limit(limit).all()
    return clients

@router.get("/{client_id}", response_model=schemas.ClientInDB)
def read_client(
    client_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Obter cliente específico."""
    client = db.query(models.Client).filter(
        models.Client.id == client_id,
        models.Client.law_firm_id == current_user.law_firm_id
    ).first()
    
    if not client:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")
    
    return client
@router.get("/with-active-cases", response_model=List[schemas.ClientInDB])
def get_clients_with_active_cases(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Clientes que têm processos em andamento"""
    clients = db.query(models.Client).\
        join(models.Case, models.Case.client_id == models.Client.id).\
        filter(
            models.Client.law_firm_id == current_user.law_firm_id,
            models.Case.status.notin_(['arquivado', 'encerrado', 'finalizado'])
        ).\
        distinct().\
        all()
    
    return clients