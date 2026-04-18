from fastapi import APIRouter, Depends, HTTPException, status, Query, Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import joinedload
from typing import List, Optional
from datetime import date
import uuid

from ...database import get_db
from ... import schemas, models
from ...dependencies import get_current_active_user

router = APIRouter()

@router.post("/", response_model=schemas.TaskInDB, status_code=status.HTTP_201_CREATED)
async def create_task(
    task: schemas.TaskCreate,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Criar nova tarefa de forma assíncrona."""
    db_task = models.Task(
        law_firm_id=current_user.law_firm_id,
        **task.model_dump()
    )
    db.add(db_task)
    await db.commit()
    await db.refresh(db_task)
    return db_task

@router.get("/", response_model=List[schemas.TaskInDB])
async def get_all_tasks(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Listar tarefas do escritório com carregamento otimizado de relações."""
    query = select(models.Task).options(
        joinedload(models.Task.case),
        joinedload(models.Task.assigned_to_user)
    ).filter(
        models.Task.law_firm_id == current_user.law_firm_id
    ).offset(skip).limit(limit)
    
    result = await db.execute(query)
    return result.scalars().all()

@router.get("/{task_id}", response_model=schemas.TaskInDB)
async def get_task_by_id(
    task_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    query = select(models.Task).filter(
        models.Task.id == task_id,
        models.Task.law_firm_id == current_user.law_firm_id
    )
    result = await db.execute(query)
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Tarefa não encontrada")
    return task

@router.get("/case/{case_id}", response_model=List[schemas.TaskInDB])
async def get_tasks_by_case(
    case_id: uuid.UUID,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    query_case = select(models.Case).filter(
        models.Case.id == case_id,
        models.Case.law_firm_id == current_user.law_firm_id
    )
    result_case = await db.execute(query_case)
    if not result_case.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Processo não encontrado")

    query_tasks = select(models.Task).filter(
        models.Task.case_id == case_id,
        models.Task.law_firm_id == current_user.law_firm_id
    ).offset(skip).limit(limit)
    result_tasks = await db.execute(query_tasks)
    return result_tasks.scalars().all()

@router.put("/{task_id}", response_model=schemas.TaskInDB)
async def update_task(
    task_id: uuid.UUID,
    task_update: schemas.TaskUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    query = select(models.Task).filter(
        models.Task.id == task_id,
        models.Task.law_firm_id == current_user.law_firm_id
    )
    result = await db.execute(query)
    db_task = result.scalar_one_or_none()
    if not db_task: raise HTTPException(status_code=404, detail="Tarefa não encontrada")
    
    update_data = task_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_task, key, value)
    
    await db.commit()
    await db.refresh(db_task)
    return db_task

@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(
    task_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    query = select(models.Task).filter(
        models.Task.id == task_id,
        models.Task.law_firm_id == current_user.law_firm_id
    )
    result = await db.execute(query)
    db_task = result.scalar_one_or_none()
    if not db_task: raise HTTPException(status_code=404, detail="Tarefa não encontrada")
    
    await db.delete(db_task)
    await db.commit()
    return None

@router.patch("/{task_id}/status", response_model=schemas.TaskInDB)
async def update_task_status(
    task_id: uuid.UUID,
    status_val: str = Body(..., embed=True),
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    query = select(models.Task).filter(
        models.Task.id == task_id,
        models.Task.law_firm_id == current_user.law_firm_id
    )
    result = await db.execute(query)
    task = result.scalar_one_or_none()
    if not task: raise HTTPException(status_code=404, detail="Tarefa não encontrada")
    task.status = status_val
    await db.commit()
    await db.refresh(task)
    return task

@router.get("/summary/status")
async def get_tasks_count_by_status(db: AsyncSession = Depends(get_db), current_user: models.User = Depends(get_current_active_user)):
    query = select(models.Task.status, func.count(models.Task.id)).filter(models.Task.law_firm_id == current_user.law_firm_id).group_by(models.Task.status)
    result = await db.execute(query)
    return {r[0]: r[1] for r in result.all()}
