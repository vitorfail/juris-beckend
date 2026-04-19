from fastapi import APIRouter, Depends, HTTPException, status, Query, Body
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List, Optional
import uuid
import csv
from io import StringIO
from datetime import datetime

from ...database import get_db
from ... import schemas, models
from ...dependencies import get_current_active_user, get_current_admin_user

router = APIRouter()

@router.get("", response_model=List[schemas.LawFirmInDB])
@router.get("/", response_model=List[schemas.LawFirmInDB])
async def get_all_law_firms(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_admin_user)
):
    query = select(models.LawFirm).offset(skip).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()

@router.get("/{law_firm_id}", response_model=schemas.LawFirmInDB)
async def get_law_firm_by_id(
    law_firm_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    query = select(models.LawFirm).filter(models.LawFirm.id == law_firm_id)
    result = await db.execute(query)
    law_firm = result.scalar_one_or_none()
    if not law_firm:
        raise HTTPException(status_code=404, detail="Escritório não encontrado")
    return law_firm

@router.post("/criar-firma", response_model=schemas.LawFirmInDB, status_code=status.HTTP_201_CREATED)
async def create_law_firm(
    law_firm: schemas.LawFirmCreate,
    db: AsyncSession = Depends(get_db)
):
    if law_firm.cnpj:
        query_existing = select(models.LawFirm).filter(models.LawFirm.cnpj == law_firm.cnpj)
        result_existing = await db.execute(query_existing)
        if result_existing.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="CNPJ já cadastrado")
    
    db_law_firm = models.LawFirm(**law_firm.model_dump())
    db.add(db_law_firm)
    await db.commit()
    await db.refresh(db_law_firm)
    return db_law_firm

@router.put("/{law_firm_id}", response_model=schemas.LawFirmInDB)
async def update_law_firm(
    law_firm_id: uuid.UUID,
    law_firm_update: schemas.LawFirmUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_admin_user)
):
    query = select(models.LawFirm).filter(models.LawFirm.id == law_firm_id)
    result = await db.execute(query)
    law_firm = result.scalar_one_or_none()
    if not law_firm: raise HTTPException(status_code=404, detail="Escritório não encontrado")
    
    update_data = law_firm_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(law_firm, field, value)
    
    await db.commit()
    await db.refresh(law_firm)
    return law_firm

@router.patch("/{law_firm_id}/subscription", response_model=schemas.LawFirmInDB)
async def update_law_firm_subscription(
    law_firm_id: uuid.UUID, 
    plan: str = Body(..., embed=True), 
    status: str = Body(..., embed=True), 
    expires_at: Optional[datetime] = Body(None, embed=True), 
    db: AsyncSession = Depends(get_db), 
    current_user: models.User = Depends(get_current_admin_user)
):
    query = select(models.LawFirm).filter(models.LawFirm.id == law_firm_id)
    result = await db.execute(query)
    law_firm = result.scalar_one_or_none()
    if not law_firm: raise HTTPException(status_code=404, detail="Escritório não encontrado")
    
    law_firm.subscription_plan = plan
    law_firm.subscription_status = status
    law_firm.subscription_expires_at = expires_at
    
    await db.commit()
    await db.refresh(law_firm)
    return law_firm

@router.get("/{law_firm_id}/stats")
async def get_law_firm_stats(
    law_firm_id: uuid.UUID, 
    db: AsyncSession = Depends(get_db), 
    current_user: models.User = Depends(get_current_active_user)
):
    if str(law_firm_id) != str(current_user.law_firm_id): raise HTTPException(status_code=403, detail="Sem permissão")
    
    u_count = await db.execute(select(func.count(models.User.id)).filter(models.User.law_firm_id == law_firm_id))
    cl_count = await db.execute(select(func.count(models.Client.id)).filter(models.Client.law_firm_id == law_firm_id))
    ca_count = await db.execute(select(func.count(models.Case.id)).filter(models.Case.law_firm_id == law_firm_id))
    t_count = await db.execute(select(func.count(models.Task.id)).filter(models.Task.law_firm_id == law_firm_id))
    
    return {
        "users": u_count.scalar(),
        "clients": cl_count.scalar(),
        "cases": ca_count.scalar(),
        "tasks": t_count.scalar()
    }

@router.get("/{law_firm_id}/financial-summary")
async def get_law_firm_financial_summary(
    law_firm_id: uuid.UUID, 
    db: AsyncSession = Depends(get_db), 
    current_user: models.User = Depends(get_current_active_user)
):
    if str(law_firm_id) != str(current_user.law_firm_id): raise HTTPException(status_code=403, detail="Sem permissão")
    
    case_ids_query = select(models.Case.id).filter(models.Case.law_firm_id == law_firm_id)
    case_ids_result = await db.execute(case_ids_query)
    case_ids = [r[0] for r in case_ids_result.all()]
    
    if not case_ids:
        return {"total_fees": 0, "total_payments": 0, "balance": 0}
        
    records_query = select(models.FinancialRecord.type, func.sum(models.FinancialRecord.amount).label("total")).filter(
        models.FinancialRecord.case_id.in_(case_ids)
    ).group_by(models.FinancialRecord.type)
    
    result = await db.execute(records_query)
    records = result.all()
    
    fees = 0
    payments = 0
    for record in records:
        if record.type == "fee": fees = float(record.total or 0)
        elif record.type == "payment": payments = float(record.total or 0)
    return {"total_fees": fees, "total_payments": payments, "balance": fees - payments}
