from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field
import uuid

class UserLogin(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6)

    class Config:
        json_schema_extra = {
            "example": {
                "email": "admin@escritorio.com",
                "password": "123456"
            }
        }

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: uuid.UUID
    law_firm_id: uuid.UUID
    email: EmailStr
    name: str
    role: str
    is_active: bool

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
                "user_id": "123e4567-e89b-12d3-a456-426614174000",
                "law_firm_id": "123e4567-e89b-12d3-a456-426614174001",
                "email": "admin@escritorio.com",
                "name": "João Silva",
                "role": "admin",
                "is_active": True
            }
        }

class TokenRefreshResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"