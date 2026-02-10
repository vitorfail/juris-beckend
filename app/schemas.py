from datetime import date, datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field, validator
import uuid

# Base schemas
class BaseSchema(BaseModel):
    class Config:
        from_attributes = True
        json_encoders = {
            uuid.UUID: str
        }

# Law Firm
class LawFirmBase(BaseSchema):
    name: str = Field(..., max_length=255)
    cnpj: Optional[str] = Field(None, max_length=18)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=20)

class LawFirmCreate(LawFirmBase):
    pass

class LawFirmUpdate(BaseSchema):
    name: Optional[str] = Field(None, max_length=255)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=20)

class LawFirmInDB(LawFirmBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# User
class UserBase(BaseSchema):
    name: str = Field(..., max_length=255)
    email: EmailStr
    role: str = Field(..., pattern="^(admin|lawyer|assistant)$")
    is_active: bool = True

class UserCreate(UserBase):
    password: str = Field(..., min_length=6)
    law_firm_id: uuid.UUID 

class UserUpdate(BaseSchema):
    name: Optional[str] = Field(None, max_length=255)
    email: Optional[EmailStr] = None
    role: Optional[str] = Field(None, pattern="^(admin|lawyer|assistant)$")
    is_active: Optional[bool] = None

class UserInDB(UserBase):
    id: uuid.UUID
    law_firm_id: uuid.UUID
    created_at: datetime
    updated_at: datetime

class UserLogin(BaseSchema):
    email: EmailStr
    password: str

class Token(BaseSchema):
    access_token: str
    token_type: str = "bearer"
    user: UserInDB

# Client
class ClientBase(BaseSchema):
    type: str = Field(..., pattern="^(pf|pj)$")
    name: str = Field(..., max_length=255)
    document: Optional[str] = Field(None, max_length=20)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=20)
    address: Optional[str] = None

class ClientCreate(ClientBase):
    pass

class ClientUpdate(BaseSchema):
    name: Optional[str] = Field(None, max_length=255)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=20)
    address: Optional[str] = None

class ClientInDB(ClientBase):
    id: uuid.UUID
    law_firm_id: uuid.UUID
    created_at: datetime
    updated_at: datetime

# Case
class CaseBase(BaseSchema):
    client_id: uuid.UUID
    case_number: Optional[str] = Field(None, max_length=50)
    court: Optional[str] = Field(None, max_length=255)
    area: Optional[str] = Field(None, max_length=100)
    status: Optional[str] = Field(None, max_length=50)
    distribution_date: Optional[date] = None
    value: Optional[float] = None
    description: Optional[str] = None
    responsible_lawyer_id: Optional[uuid.UUID] = None

class CaseCreate(CaseBase):
    pass

class CaseUpdate(BaseSchema):
    case_number: Optional[str] = Field(None, max_length=50)
    court: Optional[str] = Field(None, max_length=255)
    status: Optional[str] = Field(None, max_length=50)
    value: Optional[float] = None
    description: Optional[str] = None
    responsible_lawyer_id: Optional[uuid.UUID] = None

class CaseInDB(CaseBase):
    id: uuid.UUID
    law_firm_id: uuid.UUID
    created_at: datetime
    updated_at: datetime

# Case Party
class CasePartyBase(BaseSchema):
    case_id: uuid.UUID
    name: str = Field(..., max_length=255)
    role: Optional[str] = Field(None, max_length=50)
    document: Optional[str] = Field(None, max_length=20)

class CasePartyCreate(CasePartyBase):
    pass

class CasePartyInDB(CasePartyBase):
    id: uuid.UUID

# Case Movement
class CaseMovementBase(BaseSchema):
    case_id: uuid.UUID
    movement_date: date
    description: Optional[str] = None

class CaseMovementCreate(CaseMovementBase):
    pass

class CaseMovementInDB(CaseMovementBase):
    id: uuid.UUID
    created_at: datetime

# Task
class TaskBase(BaseSchema):
    case_id: Optional[uuid.UUID] = None
    assigned_to: Optional[uuid.UUID] = None
    title: str = Field(..., max_length=255)
    description: Optional[str] = None
    due_date: Optional[date] = None
    status: str = Field("pending", pattern="^(pending|done|late)$")

class TaskCreate(TaskBase):
    pass

class TaskUpdate(BaseSchema):
    title: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    due_date: Optional[date] = None
    status: Optional[str] = Field(None, pattern="^(pending|done|late)$")
    assigned_to: Optional[uuid.UUID] = None

class TaskInDB(TaskBase):
    id: uuid.UUID
    law_firm_id: uuid.UUID
    created_at: datetime

# Hearing
class HearingBase(BaseSchema):
    case_id: uuid.UUID
    hearing_date: datetime
    type: Optional[str] = Field(None, max_length=100)
    location: Optional[str] = Field(None, max_length=255)
    notes: Optional[str] = None

class HearingCreate(HearingBase):
    pass

class HearingInDB(HearingBase):
    id: uuid.UUID

# Document
class DocumentBase(BaseSchema):
    case_id: uuid.UUID
    file_name: str = Field(..., max_length=255)
    file_url: str

class DocumentCreate(DocumentBase):
    pass

class DocumentInDB(DocumentBase):
    id: uuid.UUID
    uploaded_by: Optional[uuid.UUID]
    created_at: datetime

# Financial Record
class FinancialRecordBase(BaseSchema):
    case_id: uuid.UUID
    type: str = Field(..., pattern="^(fee|payment)$")
    description: Optional[str] = None
    amount: float
    due_date: Optional[date] = None
    paid_at: Optional[date] = None

class FinancialRecordCreate(FinancialRecordBase):
    pass

class FinancialRecordUpdate(BaseSchema):
    description: Optional[str] = None
    amount: Optional[float] = None
    due_date: Optional[date] = None
    paid_at: Optional[date] = None

class FinancialRecordInDB(FinancialRecordBase):
    id: uuid.UUID

# Note
class NoteBase(BaseSchema):
    case_id: uuid.UUID
    content: str

class NoteCreate(NoteBase):
    pass

class NoteInDB(NoteBase):
    id: uuid.UUID
    user_id: uuid.UUID
    created_at: datetime

# Response schemas com relações
class ClientWithCases(ClientInDB):
    cases: List[CaseInDB] = []

class CaseWithRelations(CaseInDB):
    client: Optional[ClientInDB] = None
    responsible_lawyer: Optional[UserInDB] = None
    case_parties: List[CasePartyInDB] = []
    case_movements: List[CaseMovementInDB] = []
    tasks: List[TaskInDB] = []
    hearings: List[HearingInDB] = []
    documents: List[DocumentInDB] = []
    financial_records: List[FinancialRecordInDB] = []
    notes: List[NoteInDB] = []

class UserWithRelations(UserInDB):
    law_firm: Optional[LawFirmInDB] = None