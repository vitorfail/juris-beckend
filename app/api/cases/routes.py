from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from datetime import date, datetime
import uuid
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
def get_all_cases(
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


@router.get("/{case_id}", response_model=schemas.CaseInDB)
def get_case_by_id(
    case_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Buscar processo por ID."""
    case = db.query(models.Case).filter(
        models.Case.id == case_id,
        models.Case.law_firm_id == current_user.law_firm_id
    ).first()
    if not case:
        raise HTTPException(status_code=404, detail="Processo não encontrado")
    return case


@router.get("/{case_id}/with-relations", response_model=schemas.CaseWithRelations)
def get_case_with_all_relations(
    case_id: str,
    include_movements: bool = True,
    include_tasks: bool = True,
    include_hearings: bool = True,
    include_documents: bool = True,
    include_financial: bool = True,
    include_notes: bool = True,
    include_parties: bool = True,
    include_client: bool = True,
    include_lawyer: bool = True,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Buscar processo com todas as relações."""
    case = db.query(models.Case).filter(
        models.Case.id == case_id,
        models.Case.law_firm_id == current_user.law_firm_id
    ).first()
    if not case:
        raise HTTPException(status_code=404, detail="Processo não encontrado")

    result = {**case.__dict__, "client": None, "responsible_lawyer": None, "case_parties": [], "case_movements": [], "tasks": [], "hearings": [], "documents": [], "financial_records": [], "notes": []}

    if include_client:
        result["client"] = case.client
    if include_lawyer:
        result["responsible_lawyer"] = case.responsible_lawyer
    if include_parties:
        result["case_parties"] = db.query(models.CaseParty).filter(models.CaseParty.case_id == case_id).all()
    if include_movements:
        result["case_movements"] = db.query(models.CaseMovement).filter(models.CaseMovement.case_id == case_id).order_by(models.CaseMovement.movement_date.desc()).all()
    if include_tasks:
        result["tasks"] = db.query(models.Task).filter(models.Task.case_id == case_id).all()
    if include_hearings:
        result["hearings"] = db.query(models.Hearing).filter(models.Hearing.case_id == case_id).all()
    if include_documents:
        result["documents"] = db.query(models.Document).filter(models.Document.case_id == case_id).all()
    if include_financial:
        result["financial_records"] = db.query(models.FinancialRecord).filter(models.FinancialRecord.case_id == case_id).all()
    if include_notes:
        result["notes"] = db.query(models.Note).filter(models.Note.case_id == case_id).all()

    return result


@router.get("/client/{client_id}", response_model=List[schemas.CaseInDB])
def get_cases_by_client(
    client_id: str,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Listar processos de um cliente."""
    client = db.query(models.Client).filter(
        models.Client.id == client_id,
        models.Client.law_firm_id == current_user.law_firm_id
    ).first()
    if not client:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")

    cases = db.query(models.Case).filter(
        models.Case.client_id == client_id,
        models.Case.law_firm_id == current_user.law_firm_id
    ).offset(skip).limit(limit).all()
    return cases


@router.get("/status/{status}", response_model=List[schemas.CaseInDB])
def get_cases_by_status(
    status: str,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Listar processos por status."""
    cases = db.query(models.Case).filter(
        models.Case.status == status,
        models.Case.law_firm_id == current_user.law_firm_id
    ).offset(skip).limit(limit).all()
    return cases


@router.get("/area/{area}", response_model=List[schemas.CaseInDB])
def get_cases_by_area(
    area: str,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Listar processos por área do direito."""
    cases = db.query(models.Case).filter(
        models.Case.area.ilike(f"%{area}%"),
        models.Case.law_firm_id == current_user.law_firm_id
    ).offset(skip).limit(limit).all()
    return cases


@router.get("/lawyer/{lawyer_id}", response_model=List[schemas.CaseInDB])
def get_cases_by_lawyer(
    lawyer_id: str,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Listar processos por advogado responsável."""
    lawyer = db.query(models.User).filter(
        models.User.id == lawyer_id,
        models.User.law_firm_id == current_user.law_firm_id
    ).first()
    if not lawyer:
        raise HTTPException(status_code=404, detail="Advogado não encontrado")
    cases = db.query(models.Case).filter(
        models.Case.responsible_lawyer_id == lawyer_id,
        models.Case.law_firm_id == current_user.law_firm_id
    ).offset(skip).limit(limit).all()
    return cases


@router.get("/court/{court}", response_model=List[schemas.CaseInDB])
def get_cases_by_court(
    court: str,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Listar processos por tribunal."""
    cases = db.query(models.Case).filter(
        models.Case.court.ilike(f"%{court}%"),
        models.Case.law_firm_id == current_user.law_firm_id
    ).offset(skip).limit(limit).all()
    return cases


@router.get("/date-range/", response_model=List[schemas.CaseInDB])
def get_cases_by_date_range(
    start_date: date,
    end_date: date,
    date_type: str = "created_at",
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Listar processos por intervalo de datas."""
    if start_date > end_date:
        raise HTTPException(status_code=400, detail="Data inicial não pode ser maior que data final")

    column = getattr(models.Case, date_type)
    cases = db.query(models.Case).filter(
        column >= start_date,
        column <= end_date,
        models.Case.law_firm_id == current_user.law_firm_id
    ).offset(skip).limit(limit).all()
    return cases


@router.get("/value-range/", response_model=List[schemas.CaseInDB])
def get_cases_by_value_range(
    min_value: float,
    max_value: float,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Listar processos por faixa de valor."""
    if min_value > max_value:
        raise HTTPException(status_code=400, detail="Valor mínimo não pode ser maior que valor máximo")

    cases = db.query(models.Case).filter(
        models.Case.value >= min_value,
        models.Case.value <= max_value,
        models.Case.law_firm_id == current_user.law_firm_id
    ).offset(skip).limit(limit).all()
    return cases


@router.get("/recent/", response_model=List[schemas.CaseInDB])
def get_recent_cases(
    days: int = 30,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Listar processos recentes."""
    from datetime import date, timedelta
    start_date = date.today() - timedelta(days=days)

    cases = db.query(models.Case).filter(
        models.Case.created_at >= start_date,
        models.Case.law_firm_id == current_user.law_firm_id
    ).order_by(models.Case.created_at.desc()).limit(limit).all()
    return cases


@router.get("/with-deadlines/", response_model=List[schemas.CaseInDB])
def get_cases_with_deadlines(
    days_ahead: int = 30,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Listar processos com prazos vencendo nos próximos X dias."""
    from datetime import date, timedelta
    from ... import models

    end_date = date.today() + timedelta(days=days_ahead)

    # Buscar casos que têm audiências ou tarefas com data futura
    cases_with_hearings = db.query(models.Case).join(
        models.Hearing, models.Case.id == models.Hearing.case_id
    ).filter(
        models.Hearing.hearing_date >= date.today(),
        models.Hearing.hearing_date <= end_date,
        models.Case.law_firm_id == current_user.law_firm_id
    ).distinct()

    cases_with_tasks = db.query(models.Case).join(
        models.Task, models.Case.id == models.Task.case_id
    ).filter(
        models.Task.due_date >= date.today(),
        models.Task.due_date <= end_date,
        models.Task.status != "done",
        models.Case.law_firm_id == current_user.law_firm_id
    ).distinct()

    # Combinar resultados
    all_cases = list(set(cases_with_hearings.all() + cases_with_tasks.all()))
    return all_cases


@router.get("/pending-tasks/", response_model=List[schemas.CaseInDB])
def get_cases_with_pending_tasks(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Listar processos que têm tarefas pendentes."""
    cases = db.query(models.Case).join(
        models.Task, models.Case.id == models.Task.case_id
    ).filter(
        models.Task.status == "pending",
        models.Case.law_firm_id == current_user.law_firm_id
    ).distinct().all()
    return cases


@router.get("/upcoming-hearings/", response_model=List[schemas.CaseInDB])
def get_cases_with_upcoming_hearings(
    days_ahead: int = 30,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Listar processos com audiências agendadas nos próximos X dias."""
    from datetime import date, timedelta
    from ... import models

    end_date = date.today() + timedelta(days=days_ahead)

    cases = db.query(models.Case).join(
        models.Hearing, models.Case.id == models.Hearing.case_id
    ).filter(
        models.Hearing.hearing_date >= date.today(),
        models.Hearing.hearing_date <= end_date,
        models.Case.law_firm_id == current_user.law_firm_id
    ).distinct().all()
    return cases


@router.get("/overdue-tasks/", response_model=List[schemas.CaseInDB])
def get_cases_with_overdue_tasks(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Listar processos com tarefas atrasadas."""
    from datetime import date
    from ... import models

    cases = db.query(models.Case).join(
        models.Task, models.Case.id == models.Task.case_id
    ).filter(
        models.Task.due_date < date.today(),
        models.Task.status != "done",
        models.Case.law_firm_id == current_user.law_firm_id
    ).distinct().all()
    return cases


@router.get("/by-distribution-date/", response_model=List[schemas.CaseInDB])
def get_cases_by_distribution_date(
    distribution_date: date,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Listar processos por data de distribuição."""
    cases = db.query(models.Case).filter(
        models.Case.distribution_date == distribution_date,
        models.Case.law_firm_id == current_user.law_firm_id
    ).offset(skip).limit(limit).all()
    return cases


@router.get("/search/number/{case_number}", response_model=List[schemas.CaseInDB])
def search_cases_by_number(
    case_number: str,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Buscar processos por número."""
    cases = db.query(models.Case).filter(
        models.Case.case_number.ilike(f"%{case_number}%"),
        models.Case.law_firm_id == current_user.law_firm_id
    ).offset(skip).limit(limit).all()
    return cases


@router.get("/search/description/", response_model=List[schemas.CaseInDB])
def search_cases_by_description(
    description: str,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Buscar processos por descrição."""
    cases = db.query(models.Case).filter(
        models.Case.description.ilike(f"%{description}%"),
        models.Case.law_firm_id == current_user.law_firm_id
    ).offset(skip).limit(limit).all()
    return cases


@router.post("/with-client/", response_model=schemas.CaseInDB, status_code=status.HTTP_201_CREATED)
def create_case_with_client(
    case: schemas.CaseCreate,
    client: schemas.ClientCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Criar novo processo junto com cliente."""
    # Verificar se o cliente já existe pelo documento
    existing_client = db.query(models.Client).filter(
        models.Client.document == client.document,
        models.Client.law_firm_id == current_user.law_firm_id
    ).first()

    if existing_client:
        client_id = existing_client.id
    else:
        # Criar novo cliente
        db_client = models.Client(
            law_firm_id=current_user.law_firm_id,
            **client.model_dump()
        )
        db.add(db_client)
        db.commit()
        db.refresh(db_client)
        client_id = db_client.id

    # Criar o processo
    db_case = models.Case(
        law_firm_id=current_user.law_firm_id,
        client_id=client_id,
        **case.model_dump()
    )
    db.add(db_case)
    db.commit()
    db.refresh(db_case)
    return db_case


@router.post("/with-parts/", response_model=schemas.CaseInDB, status_code=status.HTTP_201_CREATED)
def create_case_with_parts(
    case: schemas.CaseCreate,
    parts: List[schemas.CasePartyCreate],
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Criar novo processo junto com suas partes."""
    # Verificar se cliente pertence ao escritório
    client = db.query(models.Client).filter(
        models.Client.id == case.client_id,
        models.Client.law_firm_id == current_user.law_firm_id
    ).first()

    if not client:
        raise HTTPException(status_code=400, detail="Cliente não encontrado")

    # Criar o processo
    db_case = models.Case(
        law_firm_id=current_user.law_firm_id,
        **case.model_dump()
    )
    db.add(db_case)
    db.flush()  # Flush para obter o ID sem commit

    # Criar as partes
    for part_data in parts:
        db_part = models.CaseParty(
            case_id=db_case.id,
            **part_data.model_dump()
        )
        db.add(db_part)

    db.commit()
    db.refresh(db_case)
    return db_case


@router.post("/bulk/", response_model=List[schemas.CaseInDB], status_code=status.HTTP_201_CREATED)
def bulk_create_cases(
    cases: List[schemas.CaseCreate],
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Criar múltiplos processos de uma vez."""
    db_cases = []

    for case_data in cases:
        # Verificar se cliente pertence ao escritório
        client = db.query(models.Client).filter(
            models.Client.id == case_data.client_id,
            models.Client.law_firm_id == current_user.law_firm_id
        ).first()

        if not client:
            raise HTTPException(status_code=400, detail=f"Cliente não encontrado para o processo")

        # Criar o processo
        db_case = models.Case(
            law_firm_id=current_user.law_firm_id,
            **case_data.model_dump()
        )
        db.add(db_case)
        db_cases.append(db_case)

    db.commit()

    # Refresh todos os casos para obter os IDs
    for db_case in db_cases:
        db.refresh(db_case)

    return db_cases


@router.put("/{case_id}", response_model=schemas.CaseInDB)
def update_case(
    case_id: str,
    case_update: schemas.CaseUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Atualizar processo existente."""
    # Buscar o processo
    db_case = db.query(models.Case).filter(
        models.Case.id == case_id,
        models.Case.law_firm_id == current_user.law_firm_id
    ).first()

    if not db_case:
        raise HTTPException(status_code=404, detail="Processo não encontrado")

    # Verificar se cliente (se fornecido) pertence ao escritório
    if case_update.client_id:
        client = db.query(models.Client).filter(
            models.Client.id == case_update.client_id,
            models.Client.law_firm_id == current_user.law_firm_id
        ).first()

        if not client:
            raise HTTPException(status_code=400, detail="Cliente não encontrado")

    # Atualizar apenas os campos fornecidos
    update_data = case_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_case, field, value)

    db.commit()
    db.refresh(db_case)
    return db_case


@router.patch("/{case_id}/status", response_model=schemas.CaseInDB)
def update_case_status(
    case_id: str,
    status: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Atualizar apenas o status do processo."""
    if status not in ["pending", "active", "suspended", "archived", "completed"]:
        raise HTTPException(status_code=400, detail="Status inválido")

    # Buscar o processo
    db_case = db.query(models.Case).filter(
        models.Case.id == case_id,
        models.Case.law_firm_id == current_user.law_firm_id
    ).first()

    if not db_case:
        raise HTTPException(status_code=404, detail="Processo não encontrado")

    # Atualizar o status
    db_case.status = status
    db.commit()
    db.refresh(db_case)
    return db_case


@router.patch("/{case_id}/lawyer", response_model=schemas.CaseInDB)
def update_case_lawyer(
    case_id: str,
    lawyer_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Atualizar apenas o advogado responsável do processo."""
    # Verificar se o advogado pertence ao escritório
    lawyer = db.query(models.User).filter(
        models.User.id == lawyer_id,
        models.User.law_firm_id == current_user.law_firm_id,
        models.User.role == "lawyer"
    ).first()

    if not lawyer:
        raise HTTPException(status_code=404, detail="Advogado não encontrado ou não pertence ao escritório")

    # Buscar o processo
    db_case = db.query(models.Case).filter(
        models.Case.id == case_id,
        models.Case.law_firm_id == current_user.law_firm_id
    ).first()

    if not db_case:
        raise HTTPException(status_code=404, detail="Processo não encontrado")

    # Atualizar o advogado responsável
    db_case.responsible_lawyer_id = lawyer_id
    db.commit()
    db.refresh(db_case)
    return db_case


@router.patch("/{case_id}/value", response_model=schemas.CaseInDB)
def update_case_value(
    case_id: str,
    value: float,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Atualizar apenas o valor do processo."""
    # Buscar o processo
    db_case = db.query(models.Case).filter(
        models.Case.id == case_id,
        models.Case.law_firm_id == current_user.law_firm_id
    ).first()

    if not db_case:
        raise HTTPException(status_code=404, detail="Processo não encontrado")

    # Atualizar o valor
    db_case.value = value
    db.commit()
    db.refresh(db_case)
    return db_case


@router.patch("/{case_id}/court", response_model=schemas.CaseInDB)
def update_case_court(
    case_id: str,
    court: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Atualizar apenas o tribunal do processo."""
    # Buscar o processo
    db_case = db.query(models.Case).filter(
        models.Case.id == case_id,
        models.Case.law_firm_id == current_user.law_firm_id
    ).first()

    if not db_case:
        raise HTTPException(status_code=404, detail="Processo não encontrado")

    # Atualizar o tribunal
    db_case.court = court
    db.commit()
    db.refresh(db_case)
    return db_case


@router.patch("/{case_id}/number", response_model=schemas.CaseInDB)
def update_case_number(
    case_id: str,
    case_number: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Atualizar apenas o número do processo."""
    # Buscar o processo
    db_case = db.query(models.Case).filter(
        models.Case.id == case_id,
        models.Case.law_firm_id == current_user.law_firm_id
    ).first()

    if not db_case:
        raise HTTPException(status_code=404, detail="Processo não encontrado")

    # Atualizar o número do processo
    db_case.case_number = case_number
    db.commit()
    db.refresh(db_case)
    return db_case


@router.delete("/{case_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_case(
    case_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Excluir processo."""
    # Buscar o processo
    db_case = db.query(models.Case).filter(
        models.Case.id == case_id,
        models.Case.law_firm_id == current_user.law_firm_id
    ).first()

    if not db_case:
        raise HTTPException(status_code=404, detail="Processo não encontrado")

    # Excluir o processo (as relações serão excluídas em cascata)
    db.delete(db_case)
    db.commit()
    return {"message": "Processo excluído com sucesso"}


@router.patch("/{case_id}/archive", response_model=schemas.CaseInDB)
def archive_case(
    case_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Arquivar processo."""
    # Buscar o processo
    db_case = db.query(models.Case).filter(
        models.Case.id == case_id,
        models.Case.law_firm_id == current_user.law_firm_id
    ).first()

    if not db_case:
        raise HTTPException(status_code=404, detail="Processo não encontrado")

    # Arquivar o processo (alterando status para 'archived')
    db_case.status = "archived"
    db.commit()
    db.refresh(db_case)
    return db_case


@router.patch("/{case_id}/restore", response_model=schemas.CaseInDB)
def restore_case(
    case_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Restaurar processo arquivado."""
    # Buscar o processo
    db_case = db.query(models.Case).filter(
        models.Case.id == case_id,
        models.Case.law_firm_id == current_user.law_firm_id
    ).first()

    if not db_case:
        raise HTTPException(status_code=404, detail="Processo não encontrado")

    # Verificar se o processo está arquivado
    if db_case.status != "archived":
        raise HTTPException(status_code=400, detail="Processo não está arquivado")

    # Restaurar o processo (alterando status para 'pending' ou outro padrão)
    db_case.status = "pending"  # Ou outro status padrão conforme sua lógica de negócio
    db.commit()
    db.refresh(db_case)
    return db_case


@router.get("/count/status/{status}", response_model=int)
def count_cases_by_status(
    status: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Contar processos por status."""
    count = db.query(models.Case).filter(
        models.Case.status == status,
        models.Case.law_firm_id == current_user.law_firm_id
    ).count()
    return count


@router.get("/count/area/{area}", response_model=int)
def count_cases_by_area(
    area: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Contar processos por área do direito."""
    count = db.query(models.Case).filter(
        models.Case.area.ilike(f"%{area}%"),
        models.Case.law_firm_id == current_user.law_firm_id
    ).count()
    return count


@router.get("/count/court/{court}", response_model=int)
def count_cases_by_court(
    court: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Contar processos por tribunal."""
    count = db.query(models.Case).filter(
        models.Case.court.ilike(f"%{court}%"),
        models.Case.law_firm_id == current_user.law_firm_id
    ).count()
    return count


@router.get("/count/lawyer/{lawyer_id}", response_model=int)
def count_cases_by_lawyer(
    lawyer_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Contar processos por advogado responsável."""
    count = db.query(models.Case).filter(
        models.Case.responsible_lawyer_id == lawyer_id,
        models.Case.law_firm_id == current_user.law_firm_id
    ).count()
    return count


@router.get("/distribution/month/", response_model=List[dict])
def get_case_distribution_by_month(
    year: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Obter distribuição de processos por mês."""
    from sqlalchemy import extract

    query = db.query(
        extract('year', models.Case.created_at).label('year'),
        extract('month', models.Case.created_at).label('month'),
        func.count(models.Case.id).label('count')
    ).filter(
        models.Case.law_firm_id == current_user.law_firm_id
    )

    if year:
        query = query.filter(extract('year', models.Case.created_at) == year)

    results = query.group_by(
        extract('year', models.Case.created_at),
        extract('month', models.Case.created_at)
    ).order_by(
        extract('year', models.Case.created_at),
        extract('month', models.Case.created_at)
    ).all()

    return [
        {
            "year": int(result.year),
            "month": int(result.month),
            "count": result.count
        }
        for result in results
    ]


@router.get("/average/value/", response_model=float)
def get_average_case_value(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Obter valor médio dos processos."""
    from sqlalchemy import func

    avg_value = db.query(func.avg(models.Case.value)).filter(
        models.Case.law_firm_id == current_user.law_firm_id,
        models.Case.value.isnot(None)
    ).scalar()

    return float(avg_value) if avg_value else 0.0


@router.get("/total/value/", response_model=float)
def get_total_case_value(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Obter valor total dos processos."""
    from sqlalchemy import func

    total_value = db.query(func.sum(models.Case.value)).filter(
        models.Case.law_firm_id == current_user.law_firm_id,
        models.Case.value.isnot(None)
    ).scalar()

    return float(total_value) if total_value else 0.0


@router.get("/summary/", response_model=dict)
def get_cases_summary(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Obter resumo estatístico dos processos."""
    from sqlalchemy import func, case
    from datetime import date, timedelta

    # Total de processos
    total_cases = db.query(func.count(models.Case.id)).filter(
        models.Case.law_firm_id == current_user.law_firm_id
    ).scalar()

    # Processos por status
    status_counts = db.query(
        models.Case.status,
        func.count(models.Case.id)
    ).filter(
        models.Case.law_firm_id == current_user.law_firm_id
    ).group_by(models.Case.status).all()

    # Processos por área
    area_counts = db.query(
        models.Case.area,
        func.count(models.Case.id)
    ).filter(
        models.Case.law_firm_id == current_user.law_firm_id,
        models.Case.area.isnot(None)
    ).group_by(models.Case.area).limit(5).all()

    # Valor total e médio
    total_value = db.query(func.sum(models.Case.value)).filter(
        models.Case.law_firm_id == current_user.law_firm_id,
        models.Case.value.isnot(None)
    ).scalar() or 0

    avg_value = db.query(func.avg(models.Case.value)).filter(
        models.Case.law_firm_id == current_user.law_firm_id,
        models.Case.value.isnot(None)
    ).scalar() or 0

    # Processos recentes (últimos 30 dias)
    recent_cases = db.query(func.count(models.Case.id)).filter(
        models.Case.law_firm_id == current_user.law_firm_id,
        models.Case.created_at >= date.today() - timedelta(days=30)
    ).scalar()

    # Processos com prazos vencendo (próximos 7 dias)
    upcoming_deadlines = db.query(func.count(models.Case.id)).join(
        models.Task, models.Case.id == models.Task.case_id
    ).filter(
        models.Case.law_firm_id == current_user.law_firm_id,
        models.Task.due_date >= date.today(),
        models.Task.due_date <= date.today() + timedelta(days=7),
        models.Task.status != "done"
    ).scalar()

    return {
        "total_cases": total_cases,
        "status_distribution": {status: count for status, count in status_counts},
        "top_areas": {area: count for area, count in area_counts if area},
        "total_value": float(total_value),
        "average_value": float(avg_value),
        "recent_cases": recent_cases,
        "upcoming_deadlines": upcoming_deadlines
    }


@router.post("/report/pdf/", response_model=dict)
def generate_case_report_pdf(
    case_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Gerar relatório PDF do processo."""
    # Buscar o processo com todas as relações
    case = db.query(models.Case).filter(
        models.Case.id == case_id,
        models.Case.law_firm_id == current_user.law_firm_id
    ).first()

    if not case:
        raise HTTPException(status_code=404, detail="Processo não encontrado")

    # Aqui normalmente seria integrado com uma biblioteca de PDF como ReportLab ou WeasyPrint
    # Por enquanto, retornamos um mock indicando que o PDF seria gerado
    return {
        "message": "Relatório PDF gerado com sucesso",
        "case_id": case_id,
        "report_type": "case_details",
        "generated_at": datetime.now().isoformat(),
        "download_url": f"/reports/case_{case_id}.pdf"  # URL fictícia
    }


@router.post("/report/list/", response_model=dict)
def generate_cases_list_report(
    filters: dict = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Gerar relatório PDF da lista de processos com filtros opcionais."""
    # Construir query base
    query = db.query(models.Case).filter(
        models.Case.law_firm_id == current_user.law_firm_id
    )

    # Aplicar filtros se fornecidos
    if filters:
        if filters.get('status'):
            query = query.filter(models.Case.status == filters['status'])
        if filters.get('area'):
            query = query.filter(models.Case.area.ilike(f"%{filters['area']}%"))
        if filters.get('lawyer_id'):
            query = query.filter(models.Case.responsible_lawyer_id == filters['lawyer_id'])
        if filters.get('client_id'):
            query = query.filter(models.Case.client_id == filters['client_id'])
        if filters.get('date_from'):
            query = query.filter(models.Case.created_at >= filters['date_from'])
        if filters.get('date_to'):
            query = query.filter(models.Case.created_at <= filters['date_to'])

    cases = query.all()

    # Aqui normalmente seria integrado com uma biblioteca de PDF
    # Por enquanto, retornamos um mock indicando que o PDF seria gerado
    return {
        "message": "Relatório PDF da lista de processos gerado com sucesso",
        "total_cases": len(cases),
        "filters_applied": filters or {},
        "report_type": "cases_list",
        "generated_at": datetime.now().isoformat(),
        "download_url": f"/reports/cases_list_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"  # URL fictícia
    }


@router.get("/export/csv/", response_model=dict)
def export_cases_to_csv(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Exportar lista de processos para CSV."""
    import csv
    import io
    from fastapi.responses import StreamingResponse

    # Buscar todos os processos do escritório
    cases = db.query(models.Case).filter(
        models.Case.law_firm_id == current_user.law_firm_id
    ).all()

    # Criar buffer de memória para o CSV
    output = io.StringIO()
    writer = csv.writer(output)

    # Cabeçalho
    writer.writerow([
        'ID', 'Número', 'Tribunal', 'Área', 'Status', 'Valor',
        'Data Distribuição', 'Descrição', 'Cliente ID', 'Advogado Responsável ID',
        'Data Criação', 'Data Atualização'
    ])

    # Dados
    for case in cases:
        writer.writerow([
            str(case.id),
            case.case_number or '',
            case.court or '',
            case.area or '',
            case.status or '',
            float(case.value) if case.value else 0.0,
            case.distribution_date.isoformat() if case.distribution_date else '',
            case.description or '',
            str(case.client_id),
            str(case.responsible_lawyer_id) if case.responsible_lawyer_id else '',
            case.created_at.isoformat(),
            case.updated_at.isoformat()
        ])

    # Preparar resposta
    output.seek(0)

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=cases_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"}
    )


@router.get("/{case_id}/timeline/", response_model=List[dict])
def get_case_timeline(
    case_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Obter linha do tempo do processo com todos os eventos."""
    # Buscar o processo
    case = db.query(models.Case).filter(
        models.Case.id == case_id,
        models.Case.law_firm_id == current_user.law_firm_id
    ).first()

    if not case:
        raise HTTPException(status_code=404, detail="Processo não encontrado")

    timeline_events = []

    # Adicionar criação do processo
    timeline_events.append({
        "date": case.created_at,
        "type": "case_created",
        "title": "Processo criado",
        "description": f"Processo {case.case_number or 'sem número'} foi criado",
        "icon": "folder-plus",
        "color": "blue"
    })

    # Adicionar movimentações processuais
    movements = db.query(models.CaseMovement).filter(
        models.CaseMovement.case_id == case_id
    ).order_by(models.CaseMovement.movement_date).all()

    for movement in movements:
        timeline_events.append({
            "date": movement.movement_date,
            "type": "case_movement",
            "title": "Movimentação processual",
            "description": movement.description or "Movimentação processual registrada",
            "icon": "layers",
            "color": "green"
        })

    # Adicionar audiências
    hearings = db.query(models.Hearing).filter(
        models.Hearing.case_id == case_id
    ).order_by(models.Hearing.hearing_date).all()

    for hearing in hearings:
        timeline_events.append({
            "date": hearing.hearing_date,
            "type": "hearing",
            "title": f"Audiência: {hearing.type or 'Não especificada'}",
            "description": hearing.notes or f"Audiência em {hearing.location or 'local não especificado'}",
            "icon": "calendar-check",
            "color": "orange"
        })

    # Adicionar tarefas
    tasks = db.query(models.Task).filter(
        models.Task.case_id == case_id
    ).order_by(models.Task.due_date).all()

    for task in tasks:
        timeline_events.append({
            "date": task.due_date or task.created_at,
            "type": "task",
            "title": f"Tarefa: {task.title}",
            "description": task.description or "Tarefa pendente",
            "icon": "list-check",
            "color": "purple"
        })

    # Adicionar documentos
    documents = db.query(models.Document).filter(
        models.Document.case_id == case_id
    ).order_by(models.Document.created_at).all()

    for document in documents:
        timeline_events.append({
            "date": document.created_at,
            "type": "document",
            "title": f"Documento: {document.file_name}",
            "description": "Documento anexado ao processo",
            "icon": "paperclip",
            "color": "brown"
        })

    # Adicionar notas
    notes = db.query(models.Note).filter(
        models.Note.case_id == case_id
    ).order_by(models.Note.created_at).all()

    for note in notes:
        timeline_events.append({
            "date": note.created_at,
            "type": "note",
            "title": "Nota adicionada",
            "description": note.content[:100] + ("..." if len(note.content) > 100 else ""),
            "icon": "sticky-note",
            "color": "yellow"
        })

    # Adicionar registros financeiros
    financials = db.query(models.FinancialRecord).filter(
        models.FinancialRecord.case_id == case_id
    ).order_by(models.FinancialRecord.due_date).all()

    for financial in financials:
        timeline_events.append({
            "date": financial.due_date or financial.created_at,
            "type": "financial",
            "title": f"Lançamento financeiro: {financial.type}",
            "description": f"{financial.description or 'Lançamento'} - R$ {financial.amount}",
            "icon": "credit-card",
            "color": "red"
        })

    # Ordenar todos os eventos por data
    timeline_events.sort(key=lambda x: x["date"] if x["date"] else datetime.min)

    return timeline_events