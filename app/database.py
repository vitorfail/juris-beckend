# database.py CORRIGIDO
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator
from .config import settings
import logging

# Desative logs verbose
logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)

# Engine OTIMIZADO para banco REMOTO
engine = create_engine(
    settings.DATABASE_URL,
    
    # ⚡ CONFIGURAÇÕES PARA BANCO REMOTO:
    echo=False,  # CRÍTICO: False sempre
    echo_pool=False,
    
    # Pool para alta latência
    pool_size=20,           # REDUZIDO para conexões simultâneas
    max_overflow=30,        # Overflow limitado
    pool_pre_ping=True,    # IMPORTANTE para conexões instáveis
    pool_recycle=3600,     # Recicla a cada hora
    pool_timeout=30,       # Timeout para pegar conexão
    
    # ⏱️ Timeouts maiores para rede
    connect_args={
        "connect_timeout": 10,      # Aumentado para rede
        "keepalives": 1,
        "keepalives_idle": 60,
        "keepalives_interval": 30,
        "keepalives_count": 5,
        "sslmode": "require",       # ← OBRIGATÓRIO para Render.com!
        "sslrootcert": "",          # Usa certificados do sistema
        "application_name": "juris_api",
    }
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False  # Melhora performance
)

Base = declarative_base()

def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()