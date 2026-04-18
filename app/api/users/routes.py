from fastapi import APIRouter, Depends, HTTPException, status, Query, Body
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import joinedload
from typing import List, Optional
import uuid
from datetime import date, datetime

from ...database import get_db
from ... import schemas, models
from ...dependencies import get_current_active_user, get_current_admin_user
from ...core.security import get_password_hash, verify_password

router = APIRouter()

@router.post("/register", response_model=schemas.UserInDB, status_code=status.HTTP_201_CREATED)
async def create_user(
    user: schemas.UserCreate,
    db: AsyncSession = Depends(get_db)
):
    """Registrar novo usuário de forma assíncrona."""
    # Verificar se email já existe
    query_existing = select(models.User).filter(models.User.email == user.email)
    result_existing = await db.execute(query_existing)
    if result_existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email já registrado")
    
    # Verificar se law_firm existe
    query_firm = select(models.LawFirm).filter(models.LawFirm.id == user.law_firm_id)
    result_firm = await db.execute(query_firm)
    if not result_firm.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Escritório não encontrado")
    
    db_user = models.User(
        law_firm_id=user.law_firm_id,
        name=user.name,
        email=user.email,
        password_hash=get_password_hash(user.password),
        role=user.role,
        is_active=user.is_active,
        permissions=user.permissions
    )
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    return db_user

@router.get("/me", response_model=schemas.UserInDB)
async def read_current_user(
    current_user: models.User = Depends(get_current_active_user)
):
    return current_user

@router.get("/", response_model=List[schemas.UserInDB])
async def get_all_users(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_admin_user)
):
    # Exemplo de joinedload: Carregar o escritório junto com o usuário (Opcional)
    query = select(models.User).options(joinedload(models.User.law_firm)).filter(
        models.User.law_firm_id == current_user.law_firm_id
    ).offset(skip).limit(limit)
    
    result = await db.execute(query)
    return result.scalars().all()

@router.get("/id/{user_id}", response_model=schemas.UserInDB)
async def get_user_by_id(user_id: uuid.UUID, db: AsyncSession = Depends(get_db), current_user: models.User = Depends(get_current_active_user)):
    query = select(models.User).filter(models.User.id == user_id, models.User.law_firm_id == current_user.law_firm_id)
    result = await db.execute(query)
    user = result.scalar_one_or_none()
    if not user: raise HTTPException(status_code=404, detail="Usuário não encontrado")
    return user

@router.get("/email/{email}", response_model=schemas.UserInDB)
async def get_user_by_email(email: str, db: AsyncSession = Depends(get_db), current_user: models.User = Depends(get_current_active_user)):
    query = select(models.User).filter(models.User.email == email, models.User.law_firm_id == current_user.law_firm_id)
    result = await db.execute(query)
    user = result.scalar_one_or_none()
    if not user: raise HTTPException(status_code=404, detail="Usuário não encontrado")
    return user

@router.get("/status/active", response_model=List[schemas.UserInDB])
async def get_active_users(skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db), current_user: models.User = Depends(get_current_active_user)):
    query = select(models.User).filter(models.User.law_firm_id == current_user.law_firm_id, models.User.is_active == True).offset(skip).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()

@router.get("/status/inactive", response_model=List[schemas.UserInDB])
async def get_inactive_users(skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db), current_user: models.User = Depends(get_current_active_user)):
    query = select(models.User).filter(models.User.law_firm_id == current_user.law_firm_id, models.User.is_active == False).offset(skip).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()

@router.get("/role/{role}", response_model=List[schemas.UserInDB])
async def get_users_by_role(role: str, skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db), current_user: models.User = Depends(get_current_active_user)):
    query = select(models.User).filter(models.User.law_firm_id == current_user.law_firm_id, models.User.role == role).offset(skip).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()

@router.get("/date-range/", response_model=List[schemas.UserInDB])
async def get_users_by_date_range(start_date: date, end_date: date, skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db), current_user: models.User = Depends(get_current_active_user)):
    query = select(models.User).filter(models.User.law_firm_id == current_user.law_firm_id, models.User.created_at >= start_date, models.User.created_at <= end_date).offset(skip).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()

@router.get("/law-firm/", response_model=List[schemas.UserInDB])
async def get_users_by_law_firm(skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db), current_user: models.User = Depends(get_current_active_user)):
    query = select(models.User).filter(models.User.law_firm_id == current_user.law_firm_id).offset(skip).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()

@router.get("/search/", response_model=List[schemas.UserInDB])
async def search_users(query: str, skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db), current_user: models.User = Depends(get_current_active_user)):
    stmt = select(models.User).filter(
        models.User.law_firm_id == current_user.law_firm_id, 
        (models.User.name.ilike(f"%{query}%")) | (models.User.email.ilike(f"%{query}%"))
    ).offset(skip).limit(limit)
    result = await db.execute(stmt)
    return result.scalars().all()

@router.post("/bulk/", response_model=List[schemas.UserInDB])
async def bulk_create_users(users: List[schemas.UserCreate], db: AsyncSession = Depends(get_db), current_user: models.User = Depends(get_current_admin_user)):
    db_users = []
    for u in users:
        db_user = models.User(law_firm_id=current_user.law_firm_id, name=u.name, email=u.email, password_hash=get_password_hash(u.password), role=u.role, is_active=u.is_active, permissions=u.permissions)
        db.add(db_user)
        db_users.append(db_user)
    await db.commit()
    for u in db_users: await db.refresh(u)
    return db_users

@router.put("/{user_id}", response_model=schemas.UserInDB)
async def update_user(user_id: uuid.UUID, user_update: schemas.UserUpdate, db: AsyncSession = Depends(get_db), current_user: models.User = Depends(get_current_admin_user)):
    query = select(models.User).filter(models.User.id == user_id, models.User.law_firm_id == current_user.law_firm_id)
    result = await db.execute(query)
    user = result.scalar_one_or_none()
    if not user: raise HTTPException(status_code=404, detail="Usuário não encontrado")
    update_data = user_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(user, field, value)
    await db.commit()
    await db.refresh(user)
    return user

@router.patch("/{user_id}/activate", response_model=schemas.UserInDB)
async def activate_user(user_id: uuid.UUID, db: AsyncSession = Depends(get_db), current_user: models.User = Depends(get_current_admin_user)):
    query = select(models.User).filter(models.User.id == user_id, models.User.law_firm_id == current_user.law_firm_id)
    result = await db.execute(query)
    user = result.scalar_one_or_none()
    if not user: raise HTTPException(status_code=404, detail="Usuário não encontrado")
    user.is_active = True
    await db.commit()
    await db.refresh(user)
    return user

@router.patch("/{user_id}/deactivate", response_model=schemas.UserInDB)
async def deactivate_user(user_id: uuid.UUID, db: AsyncSession = Depends(get_db), current_user: models.User = Depends(get_current_admin_user)):
    query = select(models.User).filter(models.User.id == user_id, models.User.law_firm_id == current_user.law_firm_id)
    result = await db.execute(query)
    user = result.scalar_one_or_none()
    if not user: raise HTTPException(status_code=404, detail="Usuário não encontrado")
    user.is_active = False
    await db.commit()
    await db.refresh(user)
    return user

@router.patch("/{user_id}/status", response_model=schemas.UserInDB)
async def update_user_status(user_id: uuid.UUID, is_active: bool = Body(..., embed=True), db: AsyncSession = Depends(get_db), current_user: models.User = Depends(get_current_admin_user)):
    query = select(models.User).filter(models.User.id == user_id, models.User.law_firm_id == current_user.law_firm_id)
    result = await db.execute(query)
    user = result.scalar_one_or_none()
    if not user: raise HTTPException(status_code=404, detail="Usuário não encontrado")
    user.is_active = is_active
    await db.commit()
    await db.refresh(user)
    return user

@router.patch("/{user_id}/role", response_model=schemas.UserInDB)
async def update_user_role(user_id: uuid.UUID, role: str = Body(..., embed=True), db: AsyncSession = Depends(get_db), current_user: models.User = Depends(get_current_admin_user)):
    query = select(models.User).filter(models.User.id == user_id, models.User.law_firm_id == current_user.law_firm_id)
    result = await db.execute(query)
    user = result.scalar_one_or_none()
    if not user: raise HTTPException(status_code=404, detail="Usuário não encontrado")
    user.role = role
    await db.commit()
    await db.refresh(user)
    return user

@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(user_id: uuid.UUID, db: AsyncSession = Depends(get_db), current_user: models.User = Depends(get_current_admin_user)):
    query = select(models.User).filter(models.User.id == user_id, models.User.law_firm_id == current_user.law_firm_id)
    result = await db.execute(query)
    user = result.scalar_one_or_none()
    if not user: raise HTTPException(status_code=404, detail="Usuário não encontrado")
    await db.delete(user)
    await db.commit()
    return None

@router.post("/change-password")
async def change_password(old_password: str = Body(...), new_password: str = Body(...), db: AsyncSession = Depends(get_db), current_user: models.User = Depends(get_current_active_user)):
    if not verify_password(old_password, current_user.password_hash):
        raise HTTPException(status_code=400, detail="Senha atual incorreta")
    current_user.password_hash = get_password_hash(new_password)
    await db.commit()
    return {"message": "Senha alterada com sucesso"}

@router.post("/{user_id}/reset-password")
async def reset_password(user_id: uuid.UUID, new_password: str = Body(..., embed=True), db: AsyncSession = Depends(get_db), current_user: models.User = Depends(get_current_admin_user)):
    query = select(models.User).filter(models.User.id == user_id, models.User.law_firm_id == current_user.law_firm_id)
    result = await db.execute(query)
    user = result.scalar_one_or_none()
    if not user: raise HTTPException(status_code=404, detail="Usuário não encontrado")
    user.password_hash = get_password_hash(new_password)
    await db.commit()
    return {"message": "Senha resetada com sucesso"}

@router.get("/{user_id}/permissions")
async def get_user_permissions(user_id: uuid.UUID, db: AsyncSession = Depends(get_db), current_user: models.User = Depends(get_current_active_user)):
    query = select(models.User).filter(models.User.id == user_id, models.User.law_firm_id == current_user.law_firm_id)
    result = await db.execute(query)
    user = result.scalar_one_or_none()
    if not user: raise HTTPException(status_code=404, detail="Usuário não encontrado")
    return {"permissions": user.permissions or {}}

@router.patch("/{user_id}/permissions", response_model=schemas.UserInDB)
async def update_user_permissions(user_id: uuid.UUID, permissions: dict = Body(...), db: AsyncSession = Depends(get_db), current_user: models.User = Depends(get_current_admin_user)):
    query = select(models.User).filter(models.User.id == user_id, models.User.law_firm_id == current_user.law_firm_id)
    result = await db.execute(query)
    user = result.scalar_one_or_none()
    if not user: raise HTTPException(status_code=404, detail="Usuário não encontrado")
    user.permissions = permissions
    await db.commit()
    await db.refresh(user)
    return user

@router.get("/{user_id}/activity-log", response_model=List[schemas.UserActivityLogInDB])
async def get_user_activity_log(user_id: uuid.UUID, skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db), current_user: models.User = Depends(get_current_active_user)):
    query = select(models.UserActivityLog).filter(models.UserActivityLog.user_id == user_id).order_by(models.UserActivityLog.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()

@router.get("/count/role/")
async def count_users_by_role(db: AsyncSession = Depends(get_db), current_user: models.User = Depends(get_current_active_user)):
    query = select(models.User.role, func.count(models.User.id)).filter(models.User.law_firm_id == current_user.law_firm_id).group_by(models.User.role)
    result = await db.execute(query)
    counts = result.all()
    return {c[0]: c[1] for c in counts}

@router.get("/count/status/")
async def count_users_by_status(db: AsyncSession = Depends(get_db), current_user: models.User = Depends(get_current_active_user)):
    query = select(models.User.is_active, func.count(models.User.id)).filter(models.User.law_firm_id == current_user.law_firm_id).group_by(models.User.is_active)
    result = await db.execute(query)
    counts = result.all()
    return {"active": next((c[1] for c in counts if c[0] == True), 0), "inactive": next((c[1] for c in counts if c[0] == False), 0)}

@router.get("/summary/general")
async def get_users_summary(db: AsyncSession = Depends(get_db), current_user: models.User = Depends(get_current_active_user)):
    query_total = select(func.count(models.User.id)).filter(models.User.law_firm_id == current_user.law_firm_id)
    query_active = select(func.count(models.User.id)).filter(models.User.law_firm_id == current_user.law_firm_id, models.User.is_active == True)
    
    total = (await db.execute(query_total)).scalar()
    active = (await db.execute(query_active)).scalar()
    return {"total_users": total, "active_users": active, "inactive_users": total - active}

@router.get("/{user_id}/cases-count")
async def get_user_cases_count(user_id: uuid.UUID, db: AsyncSession = Depends(get_db), current_user: models.User = Depends(get_current_active_user)):
    query = select(func.count(models.Case.id)).filter(models.Case.law_firm_id == current_user.law_firm_id, models.Case.responsible_lawyer_id == user_id)
    count = (await db.execute(query)).scalar()
    return {"cases_count": count}

@router.get("/{user_id}/tasks-count")
async def get_user_tasks_count(user_id: uuid.UUID, db: AsyncSession = Depends(get_db), current_user: models.User = Depends(get_current_active_user)):
    query = select(func.count(models.Task.id)).filter(models.Task.law_firm_id == current_user.law_firm_id, models.Task.assigned_to == user_id)
    count = (await db.execute(query)).scalar()
    return {"tasks_count": count}

@router.get("/{user_id}/hearings-count")
async def get_user_hearings_count(user_id: uuid.UUID, db: AsyncSession = Depends(get_db), current_user: models.User = Depends(get_current_active_user)):
    subq = select(models.Case.id).filter(models.Case.law_firm_id == current_user.law_firm_id, models.Case.responsible_lawyer_id == user_id).subquery()
    query = select(func.count(models.Hearing.id)).filter(models.Hearing.case_id.in_(select(subq)))
    count = (await db.execute(query)).scalar()
    return {"hearings_count": count}

@router.get("/export/pdf")
async def generate_user_report_pdf(db: AsyncSession = Depends(get_db), current_user: models.User = Depends(get_current_active_user)):
    content = "Mock PDF User Report"
    return StreamingResponse(iter([content.encode()]), media_type="application/pdf", headers={"Content-Disposition": "attachment; filename=users_report.pdf"})
