from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from ...database import get_db
from ... import schemas, models
from ...dependencies import get_current_active_user, get_current_admin_user
from ...core.security import get_password_hash

router = APIRouter()

@router.post("/register", response_model=schemas.UserInDB, status_code=status.HTTP_201_CREATED)
def create_user(
    user: schemas.UserCreate,
    db: Session = Depends(get_db)
):
    """Registrar novo usuário."""
    # Verificar se email já existe
    existing = db.query(models.User).filter(models.User.email == user.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email já registrado")
    
    # Verificar se law_firm existe
    law_firm = db.query(models.LawFirm).filter(models.LawFirm.id == user.law_firm_id).first()
    if not law_firm:
        raise HTTPException(status_code=400, detail="Escritório não encontrado")
    
    db_user = models.User(
        law_firm_id=user.law_firm_id,
        name=user.name,
        email=user.email,
        password_hash=get_password_hash(user.password),
        role=user.role,
        is_active=user.is_active
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

@router.get("/me", response_model=schemas.UserInDB)
def read_current_user(
    current_user: models.User = Depends(get_current_active_user)
):
    """Obter informações do usuário atual."""
    return current_user

@router.get("/", response_model=List[schemas.UserInDB])
def get_all_users(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_admin_user)
):
    """Listar todos os usuários (apenas admin)."""
    users = db.query(models.User).filter(
        models.User.law_firm_id == current_user.law_firm_id
    ).offset(skip).limit(limit).all()
    return users
from sqlalchemy import func
from datetime import date, datetime
import uuid
from typing import Optional
from fastapi import Query, Body
from fastapi.responses import StreamingResponse
from ...core.security import verify_password

@router.get("/id/{user_id}", response_model=schemas.UserInDB)
def get_user_by_id(user_id: uuid.UUID, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_active_user)):
    user = db.query(models.User).filter(models.User.id == user_id, models.User.law_firm_id == current_user.law_firm_id).first()
    if not user: raise HTTPException(status_code=404, detail="Usuário não encontrado")
    return user

@router.get("/email/{email}", response_model=schemas.UserInDB)
def get_user_by_email(email: str, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_active_user)):
    user = db.query(models.User).filter(models.User.email == email, models.User.law_firm_id == current_user.law_firm_id).first()
    if not user: raise HTTPException(status_code=404, detail="Usuário não encontrado")
    return user

@router.get("/status/active", response_model=List[schemas.UserInDB])
def get_active_users(skip: int = 0, limit: int = 100, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_active_user)):
    return db.query(models.User).filter(models.User.law_firm_id == current_user.law_firm_id, models.User.is_active == True).offset(skip).limit(limit).all()

@router.get("/status/inactive", response_model=List[schemas.UserInDB])
def get_inactive_users(skip: int = 0, limit: int = 100, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_active_user)):
    return db.query(models.User).filter(models.User.law_firm_id == current_user.law_firm_id, models.User.is_active == False).offset(skip).limit(limit).all()

@router.get("/role/{role}", response_model=List[schemas.UserInDB])
def get_users_by_role(role: str, skip: int = 0, limit: int = 100, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_active_user)):
    return db.query(models.User).filter(models.User.law_firm_id == current_user.law_firm_id, models.User.role == role).offset(skip).limit(limit).all()

@router.get("/date-range/", response_model=List[schemas.UserInDB])
def get_users_by_date_range(start_date: date, end_date: date, skip: int = 0, limit: int = 100, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_active_user)):
    return db.query(models.User).filter(models.User.law_firm_id == current_user.law_firm_id, models.User.created_at >= start_date, models.User.created_at <= end_date).offset(skip).limit(limit).all()

@router.get("/law-firm/", response_model=List[schemas.UserInDB])
def get_users_by_law_firm(skip: int = 0, limit: int = 100, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_active_user)):
    return db.query(models.User).filter(models.User.law_firm_id == current_user.law_firm_id).offset(skip).limit(limit).all()

@router.get("/search/", response_model=List[schemas.UserInDB])
def search_users(query: str, skip: int = 0, limit: int = 100, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_active_user)):
    return db.query(models.User).filter(models.User.law_firm_id == current_user.law_firm_id, (models.User.name.ilike(f"%{query}%")) | (models.User.email.ilike(f"%{query}%"))).offset(skip).limit(limit).all()

@router.post("/bulk/", response_model=List[schemas.UserInDB])
def bulk_create_users(users: List[schemas.UserCreate], db: Session = Depends(get_db), current_user: models.User = Depends(get_current_admin_user)):
    db_users = []
    for u in users:
        db_user = models.User(law_firm_id=current_user.law_firm_id, name=u.name, email=u.email, password_hash=get_password_hash(u.password), role=u.role, is_active=u.is_active, permissions=u.permissions)
        db.add(db_user)
        db_users.append(db_user)
    db.commit()
    for u in db_users: db.refresh(u)
    return db_users

@router.put("/{user_id}", response_model=schemas.UserInDB)
def update_user(user_id: uuid.UUID, user_update: schemas.UserUpdate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_admin_user)):
    user = db.query(models.User).filter(models.User.id == user_id, models.User.law_firm_id == current_user.law_firm_id).first()
    if not user: raise HTTPException(status_code=404, detail="Usuário não encontrado")
    update_data = user_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(user, field, value)
    db.commit()
    db.refresh(user)
    return user

@router.patch("/{user_id}/activate", response_model=schemas.UserInDB)
def activate_user(user_id: uuid.UUID, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_admin_user)):
    user = db.query(models.User).filter(models.User.id == user_id, models.User.law_firm_id == current_user.law_firm_id).first()
    if not user: raise HTTPException(status_code=404, detail="Usuário não encontrado")
    user.is_active = True
    db.commit()
    db.refresh(user)
    return user

@router.patch("/{user_id}/deactivate", response_model=schemas.UserInDB)
def deactivate_user(user_id: uuid.UUID, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_admin_user)):
    user = db.query(models.User).filter(models.User.id == user_id, models.User.law_firm_id == current_user.law_firm_id).first()
    if not user: raise HTTPException(status_code=404, detail="Usuário não encontrado")
    user.is_active = False
    db.commit()
    db.refresh(user)
    return user

@router.patch("/{user_id}/status", response_model=schemas.UserInDB)
def update_user_status(user_id: uuid.UUID, is_active: bool = Body(..., embed=True), db: Session = Depends(get_db), current_user: models.User = Depends(get_current_admin_user)):
    user = db.query(models.User).filter(models.User.id == user_id, models.User.law_firm_id == current_user.law_firm_id).first()
    if not user: raise HTTPException(status_code=404, detail="Usuário não encontrado")
    user.is_active = is_active
    db.commit()
    db.refresh(user)
    return user

@router.patch("/{user_id}/role", response_model=schemas.UserInDB)
def update_user_role(user_id: uuid.UUID, role: str = Body(..., embed=True), db: Session = Depends(get_db), current_user: models.User = Depends(get_current_admin_user)):
    user = db.query(models.User).filter(models.User.id == user_id, models.User.law_firm_id == current_user.law_firm_id).first()
    if not user: raise HTTPException(status_code=404, detail="Usuário não encontrado")
    user.role = role
    db.commit()
    db.refresh(user)
    return user

@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(user_id: uuid.UUID, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_admin_user)):
    user = db.query(models.User).filter(models.User.id == user_id, models.User.law_firm_id == current_user.law_firm_id).first()
    if not user: raise HTTPException(status_code=404, detail="Usuário não encontrado")
    db.delete(user)
    db.commit()
    return None

@router.post("/change-password")
def change_password(old_password: str = Body(...), new_password: str = Body(...), db: Session = Depends(get_db), current_user: models.User = Depends(get_current_active_user)):
    if not verify_password(old_password, current_user.password_hash):
        raise HTTPException(status_code=400, detail="Senha atual incorreta")
    current_user.password_hash = get_password_hash(new_password)
    db.commit()
    return {"message": "Senha alterada com sucesso"}

@router.post("/{user_id}/reset-password")
def reset_password(user_id: uuid.UUID, new_password: str = Body(..., embed=True), db: Session = Depends(get_db), current_user: models.User = Depends(get_current_admin_user)):
    user = db.query(models.User).filter(models.User.id == user_id, models.User.law_firm_id == current_user.law_firm_id).first()
    if not user: raise HTTPException(status_code=404, detail="Usuário não encontrado")
    user.password_hash = get_password_hash(new_password)
    db.commit()
    return {"message": "Senha resetada com sucesso"}

@router.get("/{user_id}/permissions")
def get_user_permissions(user_id: uuid.UUID, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_active_user)):
    user = db.query(models.User).filter(models.User.id == user_id, models.User.law_firm_id == current_user.law_firm_id).first()
    if not user: raise HTTPException(status_code=404, detail="Usuário não encontrado")
    return {"permissions": user.permissions or {}}

@router.patch("/{user_id}/permissions", response_model=schemas.UserInDB)
def update_user_permissions(user_id: uuid.UUID, permissions: dict = Body(...), db: Session = Depends(get_db), current_user: models.User = Depends(get_current_admin_user)):
    user = db.query(models.User).filter(models.User.id == user_id, models.User.law_firm_id == current_user.law_firm_id).first()
    if not user: raise HTTPException(status_code=404, detail="Usuário não encontrado")
    user.permissions = permissions
    db.commit()
    db.refresh(user)
    return user

@router.get("/{user_id}/activity-log", response_model=List[schemas.UserActivityLogInDB])
def get_user_activity_log(user_id: uuid.UUID, skip: int = 0, limit: int = 100, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_active_user)):
    user = db.query(models.User).filter(models.User.id == user_id, models.User.law_firm_id == current_user.law_firm_id).first()
    if not user: raise HTTPException(status_code=404, detail="Usuário não encontrado")
    return db.query(models.UserActivityLog).filter(models.UserActivityLog.user_id == user_id).order_by(models.UserActivityLog.created_at.desc()).offset(skip).limit(limit).all()

@router.get("/count/role/")
def count_users_by_role(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_active_user)):
    counts = db.query(models.User.role, func.count(models.User.id)).filter(models.User.law_firm_id == current_user.law_firm_id).group_by(models.User.role).all()
    return {c[0]: c[1] for c in counts}

@router.get("/count/status/")
def count_users_by_status(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_active_user)):
    counts = db.query(models.User.is_active, func.count(models.User.id)).filter(models.User.law_firm_id == current_user.law_firm_id).group_by(models.User.is_active).all()
    return {"active": next((c[1] for c in counts if c[0] == True), 0), "inactive": next((c[1] for c in counts if c[0] == False), 0)}

@router.get("/summary/general")
def get_users_summary(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_active_user)):
    total = db.query(models.User).filter(models.User.law_firm_id == current_user.law_firm_id).count()
    active = db.query(models.User).filter(models.User.law_firm_id == current_user.law_firm_id, models.User.is_active == True).count()
    return {"total_users": total, "active_users": active, "inactive_users": total - active}

@router.get("/{user_id}/cases-count")
def get_user_cases_count(user_id: uuid.UUID, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_active_user)):
    count = db.query(models.Case).filter(models.Case.law_firm_id == current_user.law_firm_id, models.Case.responsible_lawyer_id == user_id).count()
    return {"cases_count": count}

@router.get("/{user_id}/tasks-count")
def get_user_tasks_count(user_id: uuid.UUID, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_active_user)):
    count = db.query(models.Task).filter(models.Task.law_firm_id == current_user.law_firm_id, models.Task.assigned_to == user_id).count()
    return {"tasks_count": count}

@router.get("/{user_id}/hearings-count")
def get_user_hearings_count(user_id: uuid.UUID, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_active_user)):
    case_ids = db.query(models.Case.id).filter(models.Case.law_firm_id == current_user.law_firm_id, models.Case.responsible_lawyer_id == user_id).subquery()
    count = db.query(models.Hearing).filter(models.Hearing.case_id.in_(case_ids)).count()
    return {"hearings_count": count}

@router.get("/export/pdf")
def generate_user_report_pdf(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_active_user)):
    content = "Mock PDF User Report"
    return StreamingResponse(iter([content.encode()]), media_type="application/pdf", headers={"Content-Disposition": "attachment; filename=users_report.pdf"})
