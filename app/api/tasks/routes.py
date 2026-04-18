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
def get_all_tasks(
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
from sqlalchemy import func
from datetime import date, datetime, timedelta
import uuid

@router.get("/date-range/", response_model=List[schemas.TaskInDB])
def get_tasks_by_date_range(
    start_date: date,
    end_date: date,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Listar tarefas num intervalo de datas."""
    if start_date > end_date:
        raise HTTPException(status_code=400, detail="Data inicial maior que final")
    return db.query(models.Task).filter(
        models.Task.law_firm_id == current_user.law_firm_id,
        models.Task.due_date >= start_date,
        models.Task.due_date <= end_date
    ).offset(skip).limit(limit).all()

@router.get("/status/pending/", response_model=List[schemas.TaskInDB])
def get_pending_tasks(skip: int = 0, limit: int = 100, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_active_user)):
    return db.query(models.Task).filter(models.Task.law_firm_id == current_user.law_firm_id, models.Task.status == "pending").offset(skip).limit(limit).all()

@router.get("/status/completed/", response_model=List[schemas.TaskInDB])
def get_completed_tasks(skip: int = 0, limit: int = 100, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_active_user)):
    return db.query(models.Task).filter(models.Task.law_firm_id == current_user.law_firm_id, models.Task.status == "done").offset(skip).limit(limit).all()

@router.get("/status/overdue/", response_model=List[schemas.TaskInDB])
def get_overdue_tasks(skip: int = 0, limit: int = 100, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_active_user)):
    return db.query(models.Task).filter(models.Task.law_firm_id == current_user.law_firm_id, models.Task.due_date < date.today(), models.Task.status != "done").offset(skip).limit(limit).all()

@router.get("/due/today/", response_model=List[schemas.TaskInDB])
def get_tasks_due_today(skip: int = 0, limit: int = 100, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_active_user)):
    return db.query(models.Task).filter(models.Task.law_firm_id == current_user.law_firm_id, models.Task.due_date == date.today()).offset(skip).limit(limit).all()

@router.get("/due/this-week/", response_model=List[schemas.TaskInDB])
def get_tasks_due_this_week(skip: int = 0, limit: int = 100, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_active_user)):
    start = date.today()
    end = start + timedelta(days=7)
    return db.query(models.Task).filter(models.Task.law_firm_id == current_user.law_firm_id, models.Task.due_date >= start, models.Task.due_date <= end).offset(skip).limit(limit).all()

@router.get("/priority/{priority}", response_model=List[schemas.TaskInDB])
def get_tasks_by_priority(priority: str, skip: int = 0, limit: int = 100, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_active_user)):
    return db.query(models.Task).filter(models.Task.law_firm_id == current_user.law_firm_id, models.Task.priority == priority).offset(skip).limit(limit).all()

@router.get("/me/tasks/", response_model=List[schemas.TaskInDB])
def get_my_tasks(skip: int = 0, limit: int = 100, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_active_user)):
    return db.query(models.Task).filter(models.Task.law_firm_id == current_user.law_firm_id, models.Task.assigned_to == current_user.id).offset(skip).limit(limit).all()

@router.get("/search/text/", response_model=List[schemas.TaskInDB])
def search_tasks(query: str, skip: int = 0, limit: int = 100, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_active_user)):
    return db.query(models.Task).filter(
        models.Task.law_firm_id == current_user.law_firm_id,
        (models.Task.title.ilike(f"%{query}%")) | (models.Task.description.ilike(f"%{query}%"))
    ).offset(skip).limit(limit).all()

@router.post("/with-reminder/", response_model=schemas.TaskInDB, status_code=status.HTTP_201_CREATED)
def create_task_with_reminder(task: schemas.TaskCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_active_user)):
    db_task = models.Task(law_firm_id=current_user.law_firm_id, **task.model_dump())
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    return db_task

@router.post("/recurring/", response_model=schemas.TaskInDB, status_code=status.HTTP_201_CREATED)
def create_recurring_task(task: schemas.TaskCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_active_user)):
    db_task = models.Task(law_firm_id=current_user.law_firm_id, is_recurring=True, **task.model_dump())
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    return db_task

@router.post("/bulk/", response_model=List[schemas.TaskInDB], status_code=status.HTTP_201_CREATED)
def bulk_create_tasks(tasks: List[schemas.TaskCreate], db: Session = Depends(get_db), current_user: models.User = Depends(get_current_active_user)):
    db_tasks = []
    for task_data in tasks:
        db_task = models.Task(law_firm_id=current_user.law_firm_id, **task_data.model_dump())
        db.add(db_task)
        db_tasks.append(db_task)
    db.commit()
    for task in db_tasks:
        db.refresh(task)
    return db_tasks

@router.post("/generate-recurring/")
def generate_recurring_tasks(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_active_user)):
    """Mock da geração de tarefas recorrentes."""
    return {"message": "Tarefas recorrentes geradas (Mock)"}

@router.post("/check-overdue/")
def check_overdue_tasks_and_update(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_active_user)):
    overdue_tasks = db.query(models.Task).filter(
        models.Task.law_firm_id == current_user.law_firm_id,
        models.Task.due_date < date.today(),
        models.Task.status == "pending"
    ).all()
    count = 0
    for task in overdue_tasks:
        task.status = "late"
        count += 1
    db.commit()
    return {"updated_count": count}

@router.post("/send-reminders/")
def send_task_reminders(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_active_user)):
    """Mock do envio de lembretes."""
    return {"message": "Lembretes enviados (Mock)"}

@router.put("/{task_id}", response_model=schemas.TaskInDB)
def update_task(task_id: uuid.UUID, task_update: schemas.TaskUpdate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_active_user)):
    task = db.query(models.Task).filter(models.Task.id == task_id, models.Task.law_firm_id == current_user.law_firm_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Tarefa não encontrada")
    update_data = task_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(task, field, value)
    db.commit()
    db.refresh(task)
    return task

@router.patch("/{task_id}/complete", response_model=schemas.TaskInDB)
def complete_task(task_id: uuid.UUID, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_active_user)):
    task = db.query(models.Task).filter(models.Task.id == task_id, models.Task.law_firm_id == current_user.law_firm_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Tarefa não encontrada")
    task.status = "done"
    task.progress = 100
    db.commit()
    db.refresh(task)
    return task

@router.patch("/{task_id}/reopen", response_model=schemas.TaskInDB)
def reopen_task(task_id: uuid.UUID, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_active_user)):
    task = db.query(models.Task).filter(models.Task.id == task_id, models.Task.law_firm_id == current_user.law_firm_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Tarefa não encontrada")
    task.status = "pending"
    db.commit()
    db.refresh(task)
    return task

@router.patch("/{task_id}/reassign", response_model=schemas.TaskInDB)
def reassign_task(task_id: uuid.UUID, user_id: uuid.UUID, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_active_user)):
    task = db.query(models.Task).filter(models.Task.id == task_id, models.Task.law_firm_id == current_user.law_firm_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Tarefa não encontrada")
    task.assigned_to = user_id
    db.commit()
    db.refresh(task)
    return task

@router.patch("/{task_id}/postpone", response_model=schemas.TaskInDB)
def postpone_task(task_id: uuid.UUID, new_date: date, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_active_user)):
    task = db.query(models.Task).filter(models.Task.id == task_id, models.Task.law_firm_id == current_user.law_firm_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Tarefa não encontrada")
    task.due_date = new_date
    if task.status == "late" and new_date >= date.today():
        task.status = "pending"
    db.commit()
    db.refresh(task)
    return task

@router.patch("/{task_id}/progress", response_model=schemas.TaskInDB)
def update_task_progress(task_id: uuid.UUID, progress: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_active_user)):
    task = db.query(models.Task).filter(models.Task.id == task_id, models.Task.law_firm_id == current_user.law_firm_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Tarefa não encontrada")
    if progress < 0 or progress > 100:
        raise HTTPException(status_code=400, detail="Progresso deve ser entre 0 e 100")
    task.progress = progress
    if progress == 100:
        task.status = "done"
    db.commit()
    db.refresh(task)
    return task

@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(task_id: uuid.UUID, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_active_user)):
    task = db.query(models.Task).filter(models.Task.id == task_id, models.Task.law_firm_id == current_user.law_firm_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Tarefa não encontrada")
    db.delete(task)
    db.commit()
    return None

@router.get("/count/status/", response_model=dict)
def count_tasks_by_status(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_active_user)):
    counts = db.query(models.Task.status, func.count(models.Task.id)).filter(models.Task.law_firm_id == current_user.law_firm_id).group_by(models.Task.status).all()
    return {c[0]: c[1] for c in counts}

@router.get("/count/user/", response_model=dict)
def count_tasks_by_user(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_active_user)):
    counts = db.query(models.Task.assigned_to, func.count(models.Task.id)).filter(models.Task.law_firm_id == current_user.law_firm_id).group_by(models.Task.assigned_to).all()
    return {str(c[0]) if c[0] else "unassigned": c[1] for c in counts}

@router.get("/count/case/{case_id}", response_model=int)
def count_tasks_by_case(case_id: uuid.UUID, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_active_user)):
    return db.query(models.Task).filter(models.Task.law_firm_id == current_user.law_firm_id, models.Task.case_id == case_id).count()

@router.get("/stats/completion-rate/")
def get_task_completion_rate(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_active_user)):
    total = db.query(models.Task).filter(models.Task.law_firm_id == current_user.law_firm_id).count()
    if total == 0:
        return {"rate": 0}
    done = db.query(models.Task).filter(models.Task.law_firm_id == current_user.law_firm_id, models.Task.status == "done").count()
    return {"rate": (done / total) * 100}

@router.get("/stats/average-time/")
def get_average_task_completion_time(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_active_user)):
    """Mock da métrica de tempo médio de fechamento."""
    return {"average_days": 2.5}

@router.get("/summary/dashboard/")
def get_tasks_summary(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_active_user)):
    total = db.query(models.Task).filter(models.Task.law_firm_id == current_user.law_firm_id).count()
    pending = db.query(models.Task).filter(models.Task.law_firm_id == current_user.law_firm_id, models.Task.status == "pending").count()
    done = db.query(models.Task).filter(models.Task.law_firm_id == current_user.law_firm_id, models.Task.status == "done").count()
    late = db.query(models.Task).filter(models.Task.law_firm_id == current_user.law_firm_id, models.Task.status == "late").count()
    today = db.query(models.Task).filter(models.Task.law_firm_id == current_user.law_firm_id, models.Task.due_date == date.today()).count()
    return {
        "total": total,
        "pending": pending,
        "done": done,
        "late": late,
        "due_today": today
    }
