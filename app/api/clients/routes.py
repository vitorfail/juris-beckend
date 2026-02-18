from fastapi import APIRouter, Depends, HTTPException, Path, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from ...database import get_db
from ... import schemas, models
from ...dependencies import get_current_active_user
import uuid

router = APIRouter(prefix="/clients", tags=["clients"])  # Adicione prefix e tags

@router.post("/", response_model=schemas.ClientInDB, status_code=status.HTTP_201_CREATED)
def create_client(
    client: schemas.ClientCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Criar novo cliente."""
    # Verificar se documento já existe no mesmo escritório
    if client.document:
        # Remove pontuação para comparação mais precisa
        documento_limpo = client.document.replace('.', '').replace('/', '').replace('-', '')
        
        existing = db.query(models.Client).filter(
            models.Client.law_firm_id == current_user.law_firm_id,
            models.Client.document == client.document
        ).first()
        
        if existing:
            raise HTTPException(
                status_code=400, 
                detail="Documento já cadastrado neste escritório"
            )
    
    # Criar cliente com law_firm_id do usuário atual
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
    skip: int = Query(0, ge=0, description="Registros para pular"),
    limit: int = Query(100, ge=1, le=500, description="Limite de registros"),
    search: Optional[str] = Query(None, description="Buscar por nome ou documento"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Listar clientes do escritório."""
    query = db.query(models.Client).filter(
        models.Client.law_firm_id == current_user.law_firm_id
    )
    
    # Adicionar busca se fornecida
    if search:
        query = query.filter(
            models.Client.name.ilike(f"%{search}%") |
            models.Client.document.ilike(f"%{search}%") |
            models.Client.email.ilike(f"%{search}%")
        )
    
    clients = query.order_by(models.Client.name).offset(skip).limit(limit).all()
    return clients

@router.get("/with-active-cases", response_model=List[schemas.ClientWithCases])
def get_clients_with_active_cases(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Clientes que têm processos em andamento (não arquivados/encerrados)"""
    clients = db.query(models.Client).\
        join(models.Case, models.Case.client_id == models.Client.id).\
        filter(
            models.Client.law_firm_id == current_user.law_firm_id,
            ~models.Case.status.in_(['arquivado', 'encerrado', 'finalizado'])
        ).\
        distinct().\
        offset(skip).\
        limit(limit).\
        all()
    
    # Se quiser incluir os casos ativos de cada cliente
    for client in clients:
        client.cases = [case for case in client.cases 
                       if case.status not in ['arquivado', 'encerrado', 'finalizado']]
    
    return clients

@router.get("/{client_id}", response_model=schemas.ClientWithCases)
def read_client(
    client_id: uuid.UUID = Path(..., description="ID do cliente"),
    include_cases: bool = Query(False, description="Incluir processos do cliente"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Obter cliente específico."""
    query = db.query(models.Client).filter(
        models.Client.id == client_id,
        models.Client.law_firm_id == current_user.law_firm_id
    )
    
    # Opcionalmente carregar os casos
    if include_cases:
        from sqlalchemy.orm import joinedload
        query = query.options(joinedload(models.Client.cases))
    
    client = query.first()
    
    if not client:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")
    
    return client

@router.put("/{client_id}", response_model=schemas.ClientInDB)
def update_client(
    client_id: uuid.UUID,
    client_update: schemas.ClientUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Atualizar dados do cliente."""
    client = db.query(models.Client).filter(
        models.Client.id == client_id,
        models.Client.law_firm_id == current_user.law_firm_id
    ).first()
    
    if not client:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")
    
    # Atualizar apenas campos fornecidos
    update_data = client_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(client, field, value)
    
    db.commit()
    db.refresh(client)
    
    return client

@router.delete("/{client_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_client(
    client_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Remover cliente (soft delete)."""
    client = db.query(models.Client).filter(
        models.Client.id == client_id,
        models.Client.law_firm_id == current_user.law_firm_id
    ).first()
    
    if not client:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")
    
    # Verificar se cliente tem processos ativos
    active_cases = db.query(models.Case).filter(
        models.Case.client_id == client_id,
        ~models.Case.status.in_(['arquivado', 'encerrado', 'finalizado'])
    ).count()
    
    if active_cases > 0:
        raise HTTPException(
            status_code=400, 
            detail="Cliente não pode ser removido pois possui processos ativos"
        )
    
    db.delete(client)
    db.commit()
    
    return None