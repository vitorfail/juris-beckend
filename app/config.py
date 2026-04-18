import os
from typing import List, Optional
from urllib.parse import quote_plus
from pydantic import Field
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
    BACKEND_CORS_ORIGINS: str = "http://localhost:3000"
    
    # Database
    DATABASE_HOST: str = "localhost"
    DATABASE_PORT: str = "5432"
    DATABASE_USER: str = "postgres"
    DATABASE_PASSWORD: str = "postgres"
    DATABASE_NAME: str = "law_firm_db"
    DATABASE_URL_ENV: Optional[str] = Field(None, alias="DATABASE_URL")
    
    @property
    def DATABASE_URL(self) -> str:
        """Retorna a URL do banco, priorizando o DATABASE_URL do .env e garantindo o driver asyncpg."""
        # Tenta pegar do campo preenchido pelo Pydantic ou do ambiente
        url = self.DATABASE_URL_ENV or os.getenv("DATABASE_URL")
        
        if url:
            # Garante que use postgresql+asyncpg://
            if url.startswith("postgresql://"):
                url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
            
            # Remove parâmetros que o asyncpg não gosta (ele usa connect_args no engine se precisar)
            if "?" in url:
                base_url, query = url.split("?", 1)
                # Filtra parâmetros problemáticos
                params = [p for p in query.split("&") if not p.startswith(("sslmode=", "channel_binding="))]
                if params:
                    url = f"{base_url}?{'&'.join(params)}"
                else:
                    url = base_url
            return url
            
        # Caso não tenha no .env, reconstrói das variáveis individuais
        encoded_password = quote_plus(self.DATABASE_PASSWORD)
        return (
            f"postgresql+asyncpg://{self.DATABASE_USER}:{encoded_password}"
            f"@{self.DATABASE_HOST}:{self.DATABASE_PORT}/{self.DATABASE_NAME}"
        )
    
    @property
    def ALLOWED_ORIGINS(self) -> List[str]:
        """Retorna lista de origens CORS permitidas."""
        if not hasattr(self, 'BACKEND_CORS_ORIGINS'):
            return ["http://localhost:3000"]
        return [origin.strip() for origin in self.BACKEND_CORS_ORIGINS.split(",") if origin.strip()]
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


settings = Settings()