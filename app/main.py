from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
import logging
from .config import settings
from .database import engine
from . import models
from .api.router import api_router
from app.database import get_db,SessionLocal
from app import models

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Criar tabelas no banco de dados
models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url="/docs" if settings.ENVIRONMENT == "development" else None,
    redoc_url="/redoc" if settings.ENVIRONMENT == "development" else None,
)

# Configurar CORS
if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Incluir rotas
app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/test-db")
def test_db():
    """Teste de performance do banco de dados"""
    import time
    from sqlalchemy import text  # ← ADICIONE ESTA IMPORT
    from app.database import SessionLocal
    
    db = SessionLocal()
    results = {}
    
    try:
        # Teste 1: Conexão simples
        start = time.time()
        db.execute(text("SELECT 1"))  # ← ADICIONE text()
        results["connection_ms"] = (time.time() - start) * 1000
        
        # Teste 2: Query count
        start = time.time()
        count = db.query(models.LawFirm).count()
        results["count_query_ms"] = (time.time() - start) * 1000
        
        # Teste 3: Inserção rápida
        start = time.time()
        import uuid
        test_firm = models.LawFirm(
            id=uuid.uuid4(),
            name=f"Test Performance {int(time.time())}",
            cnpj=None,
            email=None,
            phone=None
        )
        db.add(test_firm)
        db.flush()
        results["insert_flush_ms"] = (time.time() - start) * 1000
        
        db.rollback()
        
        # Teste 4: EXPLAIN ANALYZE
        start = time.time()
        db.execute(text("EXPLAIN ANALYZE SELECT 1"))
        results["explain_ms"] = (time.time() - start) * 1000
        
        return {
            **results,
            "total_ms": sum(results.values()),
            "law_firms_count": count,
            "status": "OK" if sum(results.values()) < 100 else "FAST"  # ← 100ms é rápido!
        }
        
    except Exception as e:
        return {"error": str(e), "type": type(e).__name__}
    finally:
        db.close()
@app.get("/ping")
def ping():
    """Teste básico de performance"""
    import time
    start = time.time()
    return {
        "message": "pong",
        "response_time_ms": (time.time() - start) * 1000
    }
@app.get("/")
def read_root():
    return {
        "message": "Bem-vindo à API de Gestão de Escritório de Advocacia",
        "version": settings.VERSION,
        "docs": "/docs"
    }

@app.get("/health")
def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.ENVIRONMENT == "development"
    )
@app.get("/network-test")
def network_test():
    """Teste de latência para o banco remoto"""
    import time
    import socket
    
    host = "dpg-d64h2ff5r7bs73afur9g-a.oregon-postgres.render.com"
    
    # Teste DNS + TCP
    start = time.time()
    try:
        ip = socket.gethostbyname(host)
        dns_time = (time.time() - start) * 1000
        
        # Teste TCP
        start = time.time()
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        sock.connect((ip, 5432))
        tcp_time = (time.time() - start) * 1000
        sock.close()
        
        return {
            "host": host,
            "ip": ip,
            "dns_ms": dns_time,
            "tcp_connect_ms": tcp_time,
            "estimated_rtt_ms": (dns_time + tcp_time) * 2,  # Ida e volta
            "location": "Oregon, USA (Render.com)",
            "expected_latency": "100-300ms (Brasil → USA)",
            "diagnosis": "NORMAL" if tcp_time < 300 else "HIGH_LATENCY"
        }
        
    except Exception as e:
        return {"error": str(e)}
@app.get("/test-disk")
def test_disk():
    """Teste de velocidade do disco"""
    import time
    import tempfile
    import os
    
    # Teste write
    start = time.time()
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
        for i in range(10000):
            f.write("test " * 100)
    write_time = time.time() - start
    os.unlink(f.name)
    
    # Teste read
    start = time.time()
    with open(__file__, 'r') as f:
        content = f.read()
    read_time = time.time() - start
    
    return {
        "write_10k_lines_s": write_time,
        "read_current_file_s": read_time,
        "disk_speed": "SLOW" if write_time > 0.1 else "OK"
    }