from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from typing import AsyncGenerator
from .config import settings
import logging

# Desative logs verbose
logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)

# Engine ASSÍNCRONO otimizado para banco REMOTO
engine = create_async_engine(
    settings.DATABASE_URL,
    
    # ⚡ CONFIGURAÇÕES PARA ALTA PERFORMANCE:
    echo=False,
    
    # Pool para alta latência e concorrência
    pool_size=20,
    max_overflow=30,
    pool_pre_ping=True,
    pool_recycle=3600,
    
    # Timeouts e Keepalives
    connect_args={
        "command_timeout": 60,
        "server_settings": {
            "application_name": "juris_api_async"
        }
    }
)

AsyncSessionLocal = async_sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

Base = declarative_base()

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()