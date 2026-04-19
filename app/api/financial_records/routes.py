from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
import uuid

from ...database import get_db
from ... import schemas, models
from ...dependencies import get_current_active_user

router = APIRouter()

@router.get("/", response_model=List[schemas.FinancialRecordInDB])
async def get_all_financial_records(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Listar todos os registros financeiros dos processos do escritório."""
    # Buscar todos os IDs de processos do escritório
    case_ids_query = select(models.Case.id).filter(models.Case.law_firm_id == current_user.law_firm_id)
    case_ids_result = await db.execute(case_ids_query)
    case_ids = [r[0] for r in case_ids_result.all()]
    
    if not case_ids:
        return []
        
    query = select(models.FinancialRecord).filter(
        models.FinancialRecord.case_id.in_(case_ids)
    ).offset(skip).limit(limit)
    
    result = await db.execute(query)
    return result.scalars().all()

@router.post("/", response_model=schemas.FinancialRecordInDB, status_code=status.HTTP_201_CREATED)
async def create_financial_record(
    record: schemas.FinancialRecordCreate,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    # Verificar se o processo pertence ao escritório
    case_query = select(models.Case).filter(
        models.Case.id == record.case_id,
        models.Case.law_firm_id == current_user.law_firm_id
    )
    case_result = await db.execute(case_query)
    if not case_result.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="Acesso negado ao processo")
        
    db_record = models.FinancialRecord(**record.model_dump())
    db.add(db_record)
    await db.commit()
    await db.refresh(db_record)
    return db_record
