import os
from typing import List, Optional
from urllib.parse import quote_plus
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Configurações básicas
    PROJECT_NAME: str = "Law Firm Management API"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = "development"
    
    # Segurança
    SECRET_KEY: str = "change-this-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # CORS - como string simples
    BACKEND_CORS_ORIGINS : str = "http://localhost:3000"
    
    # Database
    DATABASE_HOST: str = "localhost"
    DATABASE_PORT: str = "5432"
    DATABASE_USER: str = "postgres"
    DATABASE_PASSWORD: str = "postgres"
    DATABASE_NAME: str = "law_firm_db"
    DATABASE_URL: Optional[str] = None
    
    @property
    def DATABASE_URL(self) -> str:
        """Constrói URL de conexão segura com encoding."""
        encoded_password = quote_plus(self.DATABASE_PASSWORD)
        return (
            f"postgresql://{self.DATABASE_USER}:{encoded_password}"
            f"@{self.DATABASE_HOST}:{self.DATABASE_PORT}/{self.DATABASE_NAME}"
        )
    
    @property
    def ALLOWED_ORIGINS(self) -> List[str]:
        """Retorna lista de origens CORS permitidas."""
        if not hasattr(self, 'CORS_ORIGINS'):
            return ["http://localhost:3000"]
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


settings = Settings()