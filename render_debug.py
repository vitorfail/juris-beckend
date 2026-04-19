import sys
import os

print("--- INICIANDO DIAGNÓSTICO DE DEPLOY ---")
print(f"Diretório atual: {os.getcwd()}")
print(f"Arquivos no diretório: {os.listdir('.')}")
print(f"Python Path: {sys.path}")

try:
    print("Tentando importar app.main...")
    from app.main import app
    print("Sucesso! O app foi importado corretamente.")
    
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    print(f"Iniciando uvicorn na porta {port}...")
    uvicorn.run(app, host="0.0.0.0", port=port)
except Exception as e:
    print("!!! ERRO AO INICIAR APP !!!")
    import traceback
    traceback.print_exc()
    sys.exit(1)
