from sqlalchemy import Column, String, Text, Boolean, Numeric, Date, DateTime, ForeignKey, CheckConstraint, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from .database import Base

class LawFirm(Base):
    __tablename__ = "law_firms"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    cnpj = Column(String(18), unique=True, nullable=True)
    email = Column(String(255))
    phone = Column(String(20))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    users = relationship("User", back_populates="law_firm")
    clients = relationship("Client", back_populates="law_firm")
    cases = relationship("Case", back_populates="law_firm")
    tasks = relationship("Task", back_populates="law_firm")

class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    law_firm_id = Column(UUID(as_uuid=True), ForeignKey("law_firms.id"), nullable=False)
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(Text, nullable=False)
    role = Column(String(50), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Constraints
    __table_args__ = (
        CheckConstraint("role IN ('admin', 'lawyer', 'assistant')", name="role_check"),
    )

    # Relationships
    law_firm = relationship("LawFirm", back_populates="users")
    cases_responsible = relationship("Case", back_populates="responsible_lawyer", foreign_keys="Case.responsible_lawyer_id")
    tasks_assigned = relationship("Task", back_populates="assigned_to_user", foreign_keys="Task.assigned_to")
    documents_uploaded = relationship("Document", back_populates="uploaded_by_user")
    notes = relationship("Note", back_populates="user")

class Client(Base):
    __tablename__ = "clients"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    law_firm_id = Column(UUID(as_uuid=True), ForeignKey("law_firms.id"), nullable=False)
    type = Column(String(20), nullable=False)
    name = Column(String(255), nullable=False)
    document = Column(String(20))
    email = Column(String(255))
    phone = Column(String(20))
    address = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    estado = Column(String(10), nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Constraints
    __table_args__ = (
        CheckConstraint("type IN ('pf', 'pj')", name="client_type_check"),
        Index("idx_client_document", "document"),
    )

    # Relationships
    law_firm = relationship("LawFirm", back_populates="clients")
    cases = relationship("Case", back_populates="client")

class Case(Base):
    __tablename__ = "cases"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    law_firm_id = Column(UUID(as_uuid=True), ForeignKey("law_firms.id"), nullable=False)
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id"), nullable=False)
    case_number = Column(String(50))
    court = Column(String(255))
    area = Column(String(100))
    status = Column(String(50))
    distribution_date = Column(Date)
    value = Column(Numeric(15, 2))
    description = Column(Text)
    responsible_lawyer_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    law_firm = relationship("LawFirm", back_populates="cases")
    client = relationship("Client", back_populates="cases")
    responsible_lawyer = relationship("User", back_populates="cases_responsible", foreign_keys=[responsible_lawyer_id])
    case_parties = relationship("CaseParty", back_populates="case", cascade="all, delete-orphan")
    case_movements = relationship("CaseMovement", back_populates="case", cascade="all, delete-orphan")
    tasks = relationship("Task", back_populates="case")
    hearings = relationship("Hearing", back_populates="case", cascade="all, delete-orphan")
    documents = relationship("Document", back_populates="case", cascade="all, delete-orphan")
    financial_records = relationship("FinancialRecord", back_populates="case", cascade="all, delete-orphan")
    notes = relationship("Note", back_populates="case", cascade="all, delete-orphan")

    # Indexes (definidos via __table_args__ para evitar duplicação)
    __table_args__ = (
        Index("idx_cases_client_id", "client_id"),
        Index("idx_cases_law_firm_id", "law_firm_id"),
    )

class CaseParty(Base):
    __tablename__ = "case_parties"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id = Column(UUID(as_uuid=True), ForeignKey("cases.id"), nullable=False)
    name = Column(String(255), nullable=False)
    role = Column(String(50))  # autor, réu, terceiro
    document = Column(String(20))

    # Relationships
    case = relationship("Case", back_populates="case_parties")

class CaseMovement(Base):
    __tablename__ = "case_movements"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id = Column(UUID(as_uuid=True), ForeignKey("cases.id"), nullable=False)
    movement_date = Column(Date, nullable=False)
    description = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    case = relationship("Case", back_populates="case_movements")

class Task(Base):
    __tablename__ = "tasks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    law_firm_id = Column(UUID(as_uuid=True), ForeignKey("law_firms.id"), nullable=False)
    case_id = Column(UUID(as_uuid=True), ForeignKey("cases.id"))
    assigned_to = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    title = Column(String(255), nullable=False)
    description = Column(Text)
    due_date = Column(Date)
    status = Column(String(30), default="pending")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Constraints
    __table_args__ = (
        CheckConstraint("status IN ('pending', 'done', 'late')", name="task_status_check"),
        Index("idx_tasks_due_date", "due_date"),
    )

    # Relationships
    law_firm = relationship("LawFirm", back_populates="tasks")
    case = relationship("Case", back_populates="tasks")
    assigned_to_user = relationship("User", back_populates="tasks_assigned", foreign_keys=[assigned_to])

class Hearing(Base):
    __tablename__ = "hearings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id = Column(UUID(as_uuid=True), ForeignKey("cases.id"), nullable=False)
    hearing_date = Column(DateTime(timezone=True), nullable=False)
    type = Column(String(100))
    location = Column(String(255))
    notes = Column(Text)

    # Relationships
    case = relationship("Case", back_populates="hearings")

class Document(Base):
    __tablename__ = "documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id = Column(UUID(as_uuid=True), ForeignKey("cases.id"), nullable=False)
    uploaded_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    file_name = Column(String(255), nullable=False)
    file_url = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    case = relationship("Case", back_populates="documents")
    uploaded_by_user = relationship("User", back_populates="documents_uploaded")

class FinancialRecord(Base):
    __tablename__ = "financial_records"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id = Column(UUID(as_uuid=True), ForeignKey("cases.id"), nullable=False)
    type = Column(String(30), nullable=False)
    description = Column(Text)
    amount = Column(Numeric(15, 2), nullable=False)
    due_date = Column(Date)
    paid_at = Column(Date)

    # Constraints
    __table_args__ = (
        CheckConstraint("type IN ('fee', 'payment')", name="financial_type_check"),
    )

    # Relationships
    case = relationship("Case", back_populates="financial_records")

class Note(Base):
    __tablename__ = "notes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id = Column(UUID(as_uuid=True), ForeignKey("cases.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    case = relationship("Case", back_populates="notes")
    user = relationship("User", back_populates="notes")