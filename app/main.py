from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
import logging
from .config import settings
from .database import engine, get_db, AsyncSessionLocal as SessionLocal
from . import models
from .api.router import api_router
from sqlalchemy import select, text
import os
# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url="/docs" if settings.ENVIRONMENT == "development" else None,
    redoc_url="/redoc" if settings.ENVIRONMENT == "development" else None,
)

# Criar tabelas no banco de dados (Modo Assíncrono)
@app.on_event("startup")
async def startup():
    try:
        logger.info("Tentando conectar ao banco de dados...")
        async with engine.begin() as conn:
            # Nota: create_all é síncrono, então usamos run_sync
            await conn.run_sync(models.Base.metadata.create_all)
        logger.info("Tabelas verificadas/criadas com sucesso.")
    except Exception as e:
        logger.error(f"ERRO CRÍTICO NO STARTUP: {str(e)}")
        # Não relançamos o erro para o servidor não morrer sem logar

# Configurar CORS - Temporariamente permissivo para debug
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def log_requests(request, call_next):
    logger.info(f"Request: {request.method} {request.url}")
    try:
        response = await call_next(request)
        logger.info(f"Response: {response.status_code}")
        return response
    except Exception as e:
        logger.error(f"Error processing request: {e}")
        raise

# Incluir rotas
app.include_router(api_router, prefix=settings.API_V1_STR)
@app.get("/debug-routes")
def debug_routes():
    routes = []
    for route in app.routes:
        routes.append({"path": route.path, "methods": list(route.methods)})
    return routes
# Rotas de debug comentadas por incompatibilidade com modo Assíncrono
# (Serão convertidas se necessário no futuro)
"""
@app.get("/test-db")
...
@app.get("/compare-raw-vs-orm")
...
"""
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
    
    host = settings.DATABASE_HOST
    logger.info(f"Testando latência para o host: '{host}'")
    
    # Teste DNS + TCP
    start = time.time()
    try:
        ip = socket.gethostbyname(host.strip())
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