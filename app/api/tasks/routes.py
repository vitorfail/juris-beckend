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