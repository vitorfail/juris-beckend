from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from ...database import get_db
from ... import schemas, models
from ...dependencies import get_current_active_user

router = APIRouter()

@router.post("/", response_model=schemas.TaskInDB, status_code=status.HTTP_201_CREATED)
def create_task(
    task: schemas.TaskCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Criar nova tarefa."""
    db_task = models.Task(
        law_firm_id=current_user.law_firm_id,
        **task.model_dump()
    )
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    return db_task

@router.get("/", response_model=List[schemas.TaskInDB])
def read_tasks(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Listar tarefas do escritório."""
    tasks = db.query(models.Task).filter(
        models.Task.law_firm_id == current_user.law_firm_id
    ).offset(skip).limit(limit).all()
    return tasks


@router.get("/{task_id}", response_model=schemas.TaskInDB)
def get_task_by_id(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Buscar tarefa por ID."""
    task = db.query(models.Task).filter(
        models.Task.id == task_id,
        models.Task.law_firm_id == current_user.law_firm_id
    ).first()
    if not task:
        raise HTTPException(status_code=404, detail="Tarefa não encontrada")
    return task


@router.get("/case/{case_id}", response_model=List[schemas.TaskInDB])
def get_tasks_by_case(
    case_id: str,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Listar tarefas de um processo específico."""
    # Verificar se o caso pertence ao escritório
    case = db.query(models.Case).filter(
        models.Case.id == case_id,
        models.Case.law_firm_id == current_user.law_firm_id
    ).first()
    if not case:
        raise HTTPException(status_code=404, detail="Processo não encontrado")

    tasks = db.query(models.Task).filter(
        models.Task.case_id == case_id,
        models.Task.law_firm_id == current_user.law_firm_id
    ).offset(skip).limit(limit).all()
    return tasks


@router.get("/assigned/{user_id}", response_model=List[schemas.TaskInDB])
def get_tasks_by_assigned_to(
    user_id: str,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Listar tarefas atribuídas a um usuário específico."""
    # Verificar se o usuário pertence ao escritório
    user = db.query(models.User).filter(
        models.User.id == user_id,
        models.User.law_firm_id == current_user.law_firm_id
    ).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    tasks = db.query(models.Task).filter(
        models.Task.assigned_to == user_id,
        models.Task.law_firm_id == current_user.law_firm_id
    ).offset(skip).limit(limit).all()
    return tasks


@router.get("/status/{status}", response_model=List[schemas.TaskInDB])
def get_tasks_by_status(
    status: str,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Listar tarefas por status."""
    # Validar status
    if status not in ["pending", "done", "late"]:
        raise HTTPException(status_code=400, detail="Status inválido. Use: pending, done ou late")

    tasks = db.query(models.Task).filter(
        models.Task.status == status,
        models.Task.law_firm_id == current_user.law_firm_id
    ).offset(skip).limit(limit).all()
    return tasks