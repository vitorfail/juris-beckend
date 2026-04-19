from fastapi import APIRouter, Depends, HTTPException, Path, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from sqlalchemy.orm import selectinload
from typing import List, Optional
import uuid

from ...database import get_db
from ... import schemas, models
from ...dependencies import get_current_active_user, get_current_token_data, TokenData

router = APIRouter()

from datetime import datetime

@router.post("/", response_model=schemas.ClientInDB, status_code=status.HTTP_201_CREATED)
async def create_client(
    client: schemas.ClientCreate,
    db: AsyncSession = Depends(get_db),
    token_data: TokenData = Depends(get_current_token_data)
):
    """Criar novo cliente otimizado para performance."""
    if client.document:
        query_existing = select(models.Client.id).filter(
            models.Client.law_firm_id == token_data.law_firm_id,
            models.Client.document == client.document
        ).limit(1)
        result_existing = await db.execute(query_existing)
        if result_existing.scalar():
            raise HTTPException(
                status_code=400, 
                detail="Documento já cadastrado neste escritório"
            )
    
    # Geramos as datas no Python para economizar um db.refresh()
    now = datetime.now()
    db_client = models.Client(
        law_firm_id=token_data.law_firm_id,
        created_at=now,
        updated_at=now,
        **client.model_dump()
    )
    
    db.add(db_client)
    await db.commit()
    return db_client

@router.get("/", response_model=schemas.ClientPagination)
async def get_all_clients(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    token_data: TokenData = Depends(get_current_token_data)
):
    query_base = select(models.Client).filter(
        models.Client.law_firm_id == token_data.law_firm_id
    )
    
    if search:
        query_base = query_base.filter(
            or_(
                models.Client.name.ilike(f"%{search}%"),
                models.Client.document.ilike(f"%{search}%"),
                models.Client.email.ilike(f"%{search}%")
            )
        )
    
    # Total count
    count_query = select(func.count()).select_from(query_base.subquery())
    total = (await db.execute(count_query)).scalar()
    
    # Paginated results
    skip = (page - 1) * size
    query = query_base.order_by(models.Client.name).offset(skip).limit(size)
    result = await db.execute(query)
    items = result.scalars().all()
    
    import math
    return {
        "items": items,
        "total": total,
        "page": page,
        "size": size,
        "pages": math.ceil(total / size) if total > 0 else 0
    }

@router.get("/with-active-cases", response_model=List[schemas.ClientWithCases])
async def get_clients_with_active_cases(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Listar clientes com casos ativos usando selectinload para performance."""
    query = select(models.Client).options(
        selectinload(models.Client.cases)
    ).join(models.Case).filter(
        models.Client.law_firm_id == current_user.law_firm_id,
        ~models.Case.status.in_(['arquivado', 'encerrado', 'finalizado'])
    ).distinct().offset(skip).limit(limit)
    
    result = await db.execute(query)
    clients = result.scalars().all()
    
    # Filtrar casos ativos na memória (ou carregar apenas eles via options se possível)
    for client in clients:
        client.cases = [case for case in client.cases 
                       if case.status not in ['arquivado', 'encerrado', 'finalizado']]
    
    return clients

@router.get("/{client_id}", response_model=schemas.ClientWithCases)
async def get_client_by_id(
    client_id: uuid.UUID,
    include_cases: bool = Query(False),
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    query = select(models.Client).filter(
        models.Client.id == client_id,
        models.Client.law_firm_id == current_user.law_firm_id
    )
    
    if include_cases:
        query = query.options(selectinload(models.Client.cases))
        
    result = await db.execute(query)
    client = result.scalar_one_or_none()
    if not client:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")
    return client

@router.put("/{client_id}", response_model=schemas.ClientInDB)
async def update_client(
    client_id: uuid.UUID,
    client_update: schemas.ClientUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    query = select(models.Client).filter(
        models.Client.id == client_id,
        models.Client.law_firm_id == current_user.law_firm_id
    )
    result = await db.execute(query)
    db_client = result.scalar_one_or_none()
    if not db_client: raise HTTPException(status_code=404, detail="Cliente não encontrado")
    
    update_data = client_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_client, key, value)
    
    await db.commit()
    await db.refresh(db_client)
    return db_client

@router.delete("/{client_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_client(
    client_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    query = select(models.Client).filter(
        models.Client.id == client_id,
        models.Client.law_firm_id == current_user.law_firm_id
    )
    result = await db.execute(query)
    db_client = result.scalar_one_or_none()
    if not db_client: raise HTTPException(status_code=404, detail="Cliente não encontrado")
    
    await db.delete(db_client)
    await db.commit()
    return None

@router.get("/search/document/{document}", response_model=schemas.ClientInDB)
async def get_client_by_document(document: str, db: AsyncSession = Depends(get_db), current_user: models.User = Depends(get_current_active_user)):
    query = select(models.Client).filter(models.Client.document == document, models.Client.law_firm_id == current_user.law_firm_id)
    result = await db.execute(query)
    client = result.scalar_one_or_none()
    if not client: raise HTTPException(status_code=404, detail="Cliente não encontrado")
    return client

@router.get("/summary/counts")
async def get_clients_counts(db: AsyncSession = Depends(get_db), current_user: models.User = Depends(get_current_active_user)):
    query_total = select(func.count(models.Client.id)).filter(models.Client.law_firm_id == current_user.law_firm_id)
    query_pj = select(func.count(models.Client.id)).filter(models.Client.law_firm_id == current_user.law_firm_id, models.Client.type == "pj")
    query_pf = select(func.count(models.Client.id)).filter(models.Client.law_firm_id == current_user.law_firm_id, models.Client.type == "pf")
    
    total = (await db.execute(query_total)).scalar()
    pj = (await db.execute(query_pj)).scalar()
    pf = (await db.execute(query_pf)).scalar()
    return {"total": total, "pj": pj, "pf": pf}

# ... (Continuarei adaptando as demais conforme o padrão)
