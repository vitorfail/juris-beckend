from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from ...database import get_db
from ... import schemas, models
from ...dependencies import get_current_active_user, get_current_admin_user

router = APIRouter()

@router.get("/", response_model=List[schemas.LawFirmInDB])
def get_all_law_firms(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_admin_user)
):
    """Listar todos os escritórios (apenas admin)."""
    law_firms = db.query(models.LawFirm).offset(skip).limit(limit).all()
    return law_firms

@router.get("/{law_firm_id}", response_model=schemas.LawFirmInDB)
def get_law_firm_by_id(
    law_firm_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Obter um escritório específico."""
    law_firm = db.query(models.LawFirm).filter(models.LawFirm.id == law_firm_id).first()
    if not law_firm:
        raise HTTPException(status_code=404, detail="Escritório não encontrado")
    return law_firm

@router.post("/criar_firma", response_model=schemas.LawFirmInDB, status_code=status.HTTP_201_CREATED)
def create_law_firm(
    law_firm: schemas.LawFirmCreate,
    db: Session = Depends(get_db)
):
    """Criar novo escritório (apenas admin)."""
    # Verificar se CNPJ já existe
    if law_firm.cnpj:
        existing = db.query(models.LawFirm).filter(models.LawFirm.cnpj == law_firm.cnpj).first()
        if existing:
            raise HTTPException(status_code=400, detail="CNPJ já cadastrado")
    
    db_law_firm = models.LawFirm(**law_firm.model_dump())
    db.add(db_law_firm)
    db.commit()
    db.refresh(db_law_firm)
    return db_law_firm

from sqlalchemy import func
from datetime import date, datetime
import uuid
import csv
from io import StringIO
from fastapi import Query, Body
from fastapi.responses import StreamingResponse

@router.get("/cnpj/{cnpj}", response_model=schemas.LawFirmInDB)
def get_law_firm_by_cnpj(cnpj: str, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_admin_user)):
    law_firm = db.query(models.LawFirm).filter(models.LawFirm.cnpj == cnpj).first()
    if not law_firm: raise HTTPException(status_code=404, detail="Escritório não encontrado")
    return law_firm

@router.get("/email/{email}", response_model=schemas.LawFirmInDB)
def get_law_firm_by_email(email: str, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_admin_user)):
    law_firm = db.query(models.LawFirm).filter(models.LawFirm.email == email).first()
    if not law_firm: raise HTTPException(status_code=404, detail="Escritório não encontrado")
    return law_firm

@router.put("/{law_firm_id}", response_model=schemas.LawFirmInDB)
def update_law_firm(law_firm_id: uuid.UUID, law_firm_update: schemas.LawFirmUpdate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_admin_user)):
    law_firm = db.query(models.LawFirm).filter(models.LawFirm.id == law_firm_id).first()
    if not law_firm: raise HTTPException(status_code=404, detail="Escritório não encontrado")
    update_data = law_firm_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(law_firm, field, value)
    db.commit()
    db.refresh(law_firm)
    return law_firm

@router.delete("/{law_firm_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_law_firm(law_firm_id: uuid.UUID, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_admin_user)):
    law_firm = db.query(models.LawFirm).filter(models.LawFirm.id == law_firm_id).first()
    if not law_firm: raise HTTPException(status_code=404, detail="Escritório não encontrado")
    db.delete(law_firm)
    db.commit()
    return None

@router.patch("/{law_firm_id}/settings", response_model=schemas.LawFirmInDB)
def update_law_firm_settings(law_firm_id: uuid.UUID, settings: dict = Body(...), db: Session = Depends(get_db), current_user: models.User = Depends(get_current_admin_user)):
    law_firm = db.query(models.LawFirm).filter(models.LawFirm.id == law_firm_id).first()
    if not law_firm: raise HTTPException(status_code=404, detail="Escritório não encontrado")
    law_firm.settings = settings
    db.commit()
    db.refresh(law_firm)
    return law_firm

@router.patch("/{law_firm_id}/subscription", response_model=schemas.LawFirmInDB)
def update_law_firm_subscription(
    law_firm_id: uuid.UUID, 
    plan: str = Body(..., embed=True), 
    status: str = Body(..., embed=True), 
    expires_at: Optional[datetime] = Body(None, embed=True), 
    db: Session = Depends(get_db), 
    current_user: models.User = Depends(get_current_admin_user)
):
    law_firm = db.query(models.LawFirm).filter(models.LawFirm.id == law_firm_id).first()
    if not law_firm: raise HTTPException(status_code=404, detail="Escritório não encontrado")
    law_firm.subscription_plan = plan
    law_firm.subscription_status = status
    law_firm.subscription_expires_at = expires_at
    db.commit()
    db.refresh(law_firm)
    return law_firm

@router.get("/{law_firm_id}/subscription")
def get_law_firm_subscription(law_firm_id: uuid.UUID, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_active_user)):
    law_firm = db.query(models.LawFirm).filter(models.LawFirm.id == law_firm_id).first()
    if not law_firm: raise HTTPException(status_code=404, detail="Escritório não encontrado")
    return {
        "plan": law_firm.subscription_plan,
        "status": law_firm.subscription_status,
        "expires_at": law_firm.subscription_expires_at
    }

@router.get("/{law_firm_id}/users", response_model=List[schemas.UserInDB])
def get_law_firm_users(law_firm_id: uuid.UUID, skip: int = 0, limit: int = 100, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_active_user)):
    if str(law_firm_id) != str(current_user.law_firm_id): raise HTTPException(status_code=403, detail="Sem permissão")
    return db.query(models.User).filter(models.User.law_firm_id == law_firm_id).offset(skip).limit(limit).all()

@router.get("/{law_firm_id}/clients", response_model=List[schemas.ClientInDB])
def get_law_firm_clients(law_firm_id: uuid.UUID, skip: int = 0, limit: int = 100, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_active_user)):
    if str(law_firm_id) != str(current_user.law_firm_id): raise HTTPException(status_code=403, detail="Sem permissão")
    return db.query(models.Client).filter(models.Client.law_firm_id == law_firm_id).offset(skip).limit(limit).all()

@router.get("/{law_firm_id}/cases", response_model=List[schemas.CaseInDB])
def get_law_firm_cases(law_firm_id: uuid.UUID, skip: int = 0, limit: int = 100, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_active_user)):
    if str(law_firm_id) != str(current_user.law_firm_id): raise HTTPException(status_code=403, detail="Sem permissão")
    return db.query(models.Case).filter(models.Case.law_firm_id == law_firm_id).offset(skip).limit(limit).all()

@router.get("/{law_firm_id}/stats")
def get_law_firm_stats(law_firm_id: uuid.UUID, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_active_user)):
    if str(law_firm_id) != str(current_user.law_firm_id): raise HTTPException(status_code=403, detail="Sem permissão")
    users_count = db.query(models.User).filter(models.User.law_firm_id == law_firm_id).count()
    clients_count = db.query(models.Client).filter(models.Client.law_firm_id == law_firm_id).count()
    cases_count = db.query(models.Case).filter(models.Case.law_firm_id == law_firm_id).count()
    tasks_count = db.query(models.Task).filter(models.Task.law_firm_id == law_firm_id).count()
    return {"users": users_count, "clients": clients_count, "cases": cases_count, "tasks": tasks_count}

@router.get("/{law_firm_id}/usage-stats")
def get_law_firm_usage_stats(law_firm_id: uuid.UUID, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_active_user)):
    if str(law_firm_id) != str(current_user.law_firm_id): raise HTTPException(status_code=403, detail="Sem permissão")
    users_count = db.query(models.User).filter(models.User.law_firm_id == law_firm_id).count()
    return {"storage_used_mb": 500, "users_count": users_count, "users_limit": 10}

@router.get("/{law_firm_id}/financial-summary")
def get_law_firm_financial_summary(law_firm_id: uuid.UUID, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_active_user)):
    if str(law_firm_id) != str(current_user.law_firm_id): raise HTTPException(status_code=403, detail="Sem permissão")
    case_ids = [c[0] for c in db.query(models.Case.id).filter(models.Case.law_firm_id == law_firm_id).all()]
    if not case_ids:
        return {"total_fees": 0, "total_payments": 0, "balance": 0}
    records = db.query(models.FinancialRecord.type, func.sum(models.FinancialRecord.amount).label("total")).filter(models.FinancialRecord.case_id.in_(case_ids)).group_by(models.FinancialRecord.type).all()
    fees = 0
    payments = 0
    for record in records:
        if record.type == "fee": fees = float(record.total or 0)
        elif record.type == "payment": payments = float(record.total or 0)
    return {"total_fees": fees, "total_payments": payments, "balance": fees - payments}

@router.get("/{law_firm_id}/export")
def export_law_firm_data(law_firm_id: uuid.UUID, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_active_user)):
    if str(law_firm_id) != str(current_user.law_firm_id): raise HTTPException(status_code=403, detail="Sem permissão")
    law_firm = db.query(models.LawFirm).filter(models.LawFirm.id == law_firm_id).first()
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "Name", "CNPJ", "Email", "Phone", "Plan", "Status"])
    writer.writerow([str(law_firm.id), law_firm.name, law_firm.cnpj, law_firm.email, law_firm.phone, law_firm.subscription_plan, law_firm.subscription_status])
    output.seek(0)
    return StreamingResponse(iter([output.getvalue()]), media_type="text/csv", headers={"Content-Disposition": f"attachment; filename=law_firm_export.csv"})

@router.get("/{law_firm_id}/report")
def generate_law_firm_report_pdf(law_firm_id: uuid.UUID, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_active_user)):
    if str(law_firm_id) != str(current_user.law_firm_id): raise HTTPException(status_code=403, detail="Sem permissão")
    content = "Mock PDF Law Firm Report"
    return StreamingResponse(iter([content.encode()]), media_type="application/pdf", headers={"Content-Disposition": "attachment; filename=law_firm_report.pdf"})
