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
def get_all_clients(
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
def get_client_by_id(
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
from sqlalchemy import func
from datetime import date, datetime
import csv
from io import StringIO
from fastapi.responses import StreamingResponse

@router.get("/filtered/", response_model=List[schemas.ClientInDB])
def get_clients_filtered(
    type: Optional[str] = None,
    estado: Optional[str] = None,
    status: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Buscar clientes com múltiplos filtros."""
    query = db.query(models.Client).filter(
        models.Client.law_firm_id == current_user.law_firm_id
    )
    if type:
        query = query.filter(models.Client.type == type)
    if estado:
        query = query.filter(models.Client.estado == estado)
    if status:
        query = query.filter(models.Client.status == status)
    
    return query.offset(skip).limit(limit).all()

@router.get("/estado/{estado}", response_model=List[schemas.ClientInDB])
def get_clients_by_estado(
    estado: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Listar clientes por estado."""
    return db.query(models.Client).filter(
        models.Client.law_firm_id == current_user.law_firm_id,
        models.Client.estado == estado
    ).offset(skip).limit(limit).all()

@router.get("/type/{client_type}", response_model=List[schemas.ClientInDB])
def get_clients_by_type(
    client_type: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Listar clientes por tipo (pf/pj)."""
    return db.query(models.Client).filter(
        models.Client.law_firm_id == current_user.law_firm_id,
        models.Client.type == client_type
    ).offset(skip).limit(limit).all()

@router.get("/recent/", response_model=List[schemas.ClientInDB])
def get_recent_clients(
    days: int = 30,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Listar clientes recentes."""
    from datetime import timedelta
    start_date = date.today() - timedelta(days=days)
    
    return db.query(models.Client).filter(
        models.Client.law_firm_id == current_user.law_firm_id,
        models.Client.created_at >= start_date
    ).order_by(models.Client.created_at.desc()).limit(limit).all()

@router.get("/search/name/{name}", response_model=List[schemas.ClientInDB])
def search_clients_by_name(
    name: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Buscar clientes por nome."""
    return db.query(models.Client).filter(
        models.Client.law_firm_id == current_user.law_firm_id,
        models.Client.name.ilike(f"%{name}%")
    ).offset(skip).limit(limit).all()

@router.get("/search/document/{document}", response_model=List[schemas.ClientInDB])
def search_clients_by_document(
    document: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Buscar clientes por documento."""
    doc_clean = document.replace('.', '').replace('-', '').replace('/', '')
    return db.query(models.Client).filter(
        models.Client.law_firm_id == current_user.law_firm_id,
        models.Client.document.like(f"%{doc_clean}%")
    ).offset(skip).limit(limit).all()

@router.get("/date-range/", response_model=List[schemas.ClientInDB])
def get_clients_by_date_range(
    start_date: date,
    end_date: date,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Listar clientes criados num intervalo de datas."""
    if start_date > end_date:
        raise HTTPException(status_code=400, detail="Data inicial maior que final")
    
    return db.query(models.Client).filter(
        models.Client.law_firm_id == current_user.law_firm_id,
        models.Client.created_at >= start_date,
        models.Client.created_at <= end_date
    ).offset(skip).limit(limit).all()

@router.get("/without-cases/", response_model=List[schemas.ClientInDB])
def get_clients_without_cases(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Listar clientes que não possuem processos vinculados."""
    clients_with_cases = db.query(models.Case.client_id).filter(
        models.Case.law_firm_id == current_user.law_firm_id
    ).distinct().subquery()
    
    return db.query(models.Client).filter(
        models.Client.law_firm_id == current_user.law_firm_id,
        models.Client.id.not_in(clients_with_cases)
    ).offset(skip).limit(limit).all()

@router.get("/check-document/{document}")
def check_client_document_exists(
    document: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Verificar se documento já existe."""
    doc_clean = document.replace('.', '').replace('-', '').replace('/', '')
    exists = db.query(models.Client).filter(
        models.Client.law_firm_id == current_user.law_firm_id,
        models.Client.document == doc_clean
    ).first() is not None
    return {"exists": exists}

@router.post("/bulk/", response_model=List[schemas.ClientInDB], status_code=status.HTTP_201_CREATED)
def bulk_create_clients(
    clients: List[schemas.ClientCreate],
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Criar múltiplos clientes em lote."""
    db_clients = []
    for client_data in clients:
        db_client = models.Client(
            law_firm_id=current_user.law_firm_id,
            **client_data.model_dump()
        )
        if db_client.document:
            db_client.document = db_client.document.replace('.', '').replace('/', '').replace('-', '')
        db.add(db_client)
        db_clients.append(db_client)
    
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail="Erro ao inserir lote, verifique duplicatas")
    
    for client in db_clients:
        db.refresh(client)
    return db_clients

@router.patch("/{client_id}/status", response_model=schemas.ClientInDB)
def update_client_status(
    client_id: uuid.UUID,
    status: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Atualizar status do cliente."""
    client = db.query(models.Client).filter(
        models.Client.id == client_id,
        models.Client.law_firm_id == current_user.law_firm_id
    ).first()
    if not client:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")
    
    client.status = status
    db.commit()
    db.refresh(client)
    return client

@router.patch("/{client_id}/archive", response_model=schemas.ClientInDB)
def archive_client(
    client_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Arquivar cliente."""
    return update_client_status(client_id, "archived", db, current_user)

@router.patch("/{client_id}/restore", response_model=schemas.ClientInDB)
def restore_client(
    client_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Restaurar cliente."""
    return update_client_status(client_id, "active", db, current_user)

@router.get("/count/type/{client_type}", response_model=int)
def count_clients_by_type(
    client_type: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Contar clientes por tipo."""
    return db.query(models.Client).filter(
        models.Client.law_firm_id == current_user.law_firm_id,
        models.Client.type == client_type
    ).count()

@router.get("/count/estado/{estado}", response_model=int)
def count_clients_by_estado(
    estado: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Contar clientes por estado."""
    return db.query(models.Client).filter(
        models.Client.law_firm_id == current_user.law_firm_id,
        models.Client.estado == estado
    ).count()

@router.get("/summary/general")
def get_clients_summary(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Resumo geral de clientes."""
    total = db.query(models.Client).filter(models.Client.law_firm_id == current_user.law_firm_id).count()
    active = db.query(models.Client).filter(models.Client.law_firm_id == current_user.law_firm_id, models.Client.status == "active").count()
    archived = db.query(models.Client).filter(models.Client.law_firm_id == current_user.law_firm_id, models.Client.status == "archived").count()
    pf = db.query(models.Client).filter(models.Client.law_firm_id == current_user.law_firm_id, models.Client.type == "pf").count()
    pj = db.query(models.Client).filter(models.Client.law_firm_id == current_user.law_firm_id, models.Client.type == "pj").count()
    
    return {
        "total": total,
        "active": active,
        "archived": archived,
        "by_type": {"pf": pf, "pj": pj}
    }

@router.get("/{client_id}/cases-summary")
def get_client_cases_summary(
    client_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Resumo de processos de um cliente."""
    client = db.query(models.Client).filter(
        models.Client.id == client_id,
        models.Client.law_firm_id == current_user.law_firm_id
    ).first()
    if not client:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")
    
    total = db.query(models.Case).filter(models.Case.client_id == client_id).count()
    active = db.query(models.Case).filter(
        models.Case.client_id == client_id,
        ~models.Case.status.in_(['arquivado', 'encerrado', 'finalizado'])
    ).count()
    
    return {
        "total_cases": total,
        "active_cases": active,
        "finished_cases": total - active
    }

@router.get("/{client_id}/financial-summary")
def get_client_financial_summary(
    client_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Resumo financeiro de um cliente."""
    client = db.query(models.Client).filter(
        models.Client.id == client_id,
        models.Client.law_firm_id == current_user.law_firm_id
    ).first()
    if not client:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")
    
    cases = db.query(models.Case.id).filter(models.Case.client_id == client_id).all()
    case_ids = [c[0] for c in cases]
    
    if not case_ids:
        return {"total_fees": 0, "total_payments": 0, "balance": 0}
        
    records = db.query(
        models.FinancialRecord.type,
        func.sum(models.FinancialRecord.amount).label("total")
    ).filter(
        models.FinancialRecord.case_id.in_(case_ids)
    ).group_by(models.FinancialRecord.type).all()
    
    fees = 0
    payments = 0
    for record in records:
        if record.type == "fee":
            fees = float(record.total or 0)
        elif record.type == "payment":
            payments = float(record.total or 0)
            
    return {
        "total_fees": fees,
        "total_payments": payments,
        "balance": fees - payments
    }

@router.get("/export/csv")
def export_clients_to_csv(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Exportar clientes em formato CSV."""
    clients = db.query(models.Client).filter(
        models.Client.law_firm_id == current_user.law_firm_id
    ).all()
    
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "Name", "Type", "Document", "Email", "Phone", "Estado", "Status", "Created At"])
    
    for client in clients:
        writer.writerow([
            str(client.id), client.name, client.type, client.document,
            client.email, client.phone, client.estado, client.status,
            client.created_at.strftime("%Y-%m-%d %H:%M:%S") if client.created_at else ""
        ])
    
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=clients_{datetime.now().strftime('%Y%m%d')}.csv"}
    )

@router.get("/export/pdf")
def generate_client_report_pdf(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Gerar relatório PDF (Mock)."""
    # Em um cenário real, utilizar reportlab ou fpdf para gerar o PDF real
    content = "PDF Report Mock Content"
    return StreamingResponse(
        iter([content.encode()]),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=clients_report_{datetime.now().strftime('%Y%m%d')}.pdf"}
    )

@router.get("/with-cases/{client_id}", response_model=schemas.ClientWithCases)
def get_client_with_cases(
    client_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Obter cliente com todos os seus processos."""
    from sqlalchemy.orm import joinedload
    client = db.query(models.Client).options(joinedload(models.Client.cases)).filter(
        models.Client.id == client_id,
        models.Client.law_firm_id == current_user.law_firm_id
    ).first()
    
    if not client:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")
    
    return client
