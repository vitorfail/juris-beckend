from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
import logging
from .config import settings
from .database import engine
from . import models
from .api.router import api_router
from app.database import get_db,SessionLocal
from app import models
import os
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
@app.get("/debug-routes")
def debug_routes():
    routes = []
    for route in app.routes:
        routes.append({"path": route.path, "methods": list(route.methods)})
    return routes
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
@app.get("/test-local-speed")
def test_local_speed():
    """Teste de velocidade com banco local"""
    import time
    from sqlalchemy import text
    from app.database import SessionLocal
    
    db = SessionLocal()
    results = {}
    
    try:
        # Teste 1: Conexão + Query
        start = time.time()
        db.execute(text("SELECT 1"))
        results["query_1"] = (time.time() - start) * 1000
        
        # Teste 2: 100 queries rápidas
        start = time.time()
        for i in range(100):
            db.execute(text("SELECT 1"))
        results["100_queries"] = (time.time() - start) * 1000
        
        # Teste 3: Insert rápido
        start = time.time()
        import uuid
        db.execute(
            text("INSERT INTO law_firms (id, name) VALUES (:id, :name)"),
            {"id": str(uuid.uuid4()), "name": "Speed Test"}
        )
        db.commit()
        results["insert_commit"] = (time.time() - start) * 1000
        
        # Rollback do teste
        db.rollback()
        
        return {
            **results,
            "expected": "< 100ms por operação",
            "diagnosis": "LOCAL_FAST" if results["query_1"] < 50 else "CHECK_CONFIG"
        }
        
    finally:
        db.close()
@app.get("/network-diagnosis")
def network_diagnosis():
    """Diagnóstico completo de rede"""
    import time
    import socket
    import subprocess
    import platform
    from urllib.parse import urlparse
    
    # Pega URL do banco do .env
    db_url = os.getenv("DATABASE_URL")
    parsed = urlparse(db_url)
    db_host = parsed.hostname
    
    results = {}
    
    # 1. DNS Resolution
    start = time.time()
    try:
        ip = socket.gethostbyname(db_host)
        results["dns_resolution_ms"] = (time.time() - start) * 1000
        results["resolved_ip"] = ip
    except Exception as e:
        results["dns_error"] = str(e)
        ip = db_host
    
    # 2. TCP Connection (socket raw)
    start = time.time()
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        sock.connect((ip, 5432))
        results["tcp_connect_ms"] = (time.time() - start) * 1000
        sock.close()
    except Exception as e:
        results["tcp_error"] = str(e)
    
    # 3. Traceroute (se permitido)
    if platform.system() != "Windows":
        try:
            trace = subprocess.run(
                ["traceroute", "-n", "-m", "10", "-q", "1", ip],
                capture_output=True,
                text=True,
                timeout=10
            )
            results["traceroute"] = trace.stdout[:500]  # Primeiros 500 chars
        except:
            results["traceroute"] = "Not available"
    
    # 4. MTR (Melhor - mostra perda de pacotes)
    if platform.system() != "Windows":
        try:
            mtr = subprocess.run(
                ["mtr", "-n", "-r", "-c", "10", ip],
                capture_output=True,
                text=True,
                timeout=15
            )
            results["mtr_report"] = mtr.stdout
        except:
            results["mtr_report"] = "Install mtr: sudo apt install mtr"
    
    # 5. Teste de banda
    start = time.time()
    try:
        # Baixa pequeno arquivo de teste
        import urllib.request
        test_url = "http://ipv4.download.thinkbroadband.com/5MB.zip"
        urllib.request.urlretrieve(test_url, "/tmp/test.zip")
        results["download_5mb_ms"] = (time.time() - start) * 1000
    except:
        results["download_test"] = "Failed"
    
    # Análise
    if "tcp_connect_ms" in results:
        latency = results["tcp_connect_ms"]
        if latency < 20:
            diagnosis = "✅ EXCELENTE (SP-SP ideal)"
        elif latency < 50:
            diagnosis = "✅ BOM (SP-SP normal)"
        elif latency < 100:
            diagnosis = "⚠️  ACEITÁVEL (possível rota ruim)"
        elif latency < 200:
            diagnosis = "❌ RUIM (problema de rota)"
        else:
            diagnosis = "🔥 HORRÍVEL (ISP ou firewall)"
        
        results["diagnosis"] = diagnosis
        results["your_latency"] = f"{latency:.1f}ms"
        results["expected_sp_sp"] = "10-30ms"
    
    return results
@app.get("/compare-raw-vs-orm")
def compare_raw_vs_orm():
    """Compara latência pura vs ORM overhead"""
    import time
    import psycopg2
    from sqlalchemy import text
    from app.database import SessionLocal
    
    db_url = os.getenv("DATABASE_URL")
    
    results = {}
    
    # 1. Psycopg2 PURO (sem ORM)
    start = time.time()
    conn = psycopg2.connect(db_url)
    cur = conn.cursor()
    cur.execute("SELECT 1")
    cur.fetchone()
    cur.close()
    conn.close()
    results["raw_psycopg2_ms"] = (time.time() - start) * 1000
    
    # 2. SQLAlchemy Core (sem ORM)
    start = time.time()
    from sqlalchemy import create_engine
    raw_engine = create_engine(db_url)
    with raw_engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    results["sqlalchemy_core_ms"] = (time.time() - start) * 1000
    
    # 3. SQLAlchemy ORM (seu setup atual)
    start = time.time()
    db = SessionLocal()
    db.execute(text("SELECT 1"))
    db.close()
    results["sqlalchemy_orm_ms"] = (time.time() - start) * 1000
    
    # 4. Seu endpoint atual (com tudo)
    # Vamos medir uma request real
    start = time.time()
    # Simula request - você pode testar manualmente
    results["full_request_estimated"] = "Teste manual seu endpoint"
    
    # Análise
    overhead_orm = results["sqlalchemy_orm_ms"] - results["raw_psycopg2_ms"]
    overhead_core = results["sqlalchemy_core_ms"] - results["raw_psycopg2_ms"]
    
    results["analysis"] = {
        "network_latency": results["raw_psycopg2_ms"],
        "orm_overhead_ms": overhead_orm,
        "orm_overhead_percent": (overhead_orm / results["raw_psycopg2_ms"]) * 100 if results["raw_psycopg2_ms"] > 0 else 0,
        "problem_is": "NETWORK" if results["raw_psycopg2_ms"] > 50 else "ORM" if overhead_orm > 50 else "OK"
    }
    
    return results
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