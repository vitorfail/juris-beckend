# debug_pydantic.py
import os
import traceback
from pydantic_settings import BaseSettings

print("=== TESTANDO PYDANTIC ===")

# Crie uma classe de teste MÍNIMA
class TestSettings(BaseSettings):
    TEST_VAR: str = "default"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

print("Tentando carregar configurações...")
try:
    settings = TestSettings()
    print("✅ Pydantic carregou com sucesso!")
    print(f"TEST_VAR = {settings.TEST_VAR}")
except Exception as e:
    print(f"❌ Erro no Pydantic: {type(e).__name__}")
    print(f"Mensagem: {e}")
    print("\nTraceback completo:")
    traceback.print_exc()

print("\n=== LENDO .env DIRETAMENTE ===")
try:
    with open('.env', 'rb') as f:
        raw = f.read()
    print(f"Arquivo .env lido: {len(raw)} bytes")
    
    # Procurar 0xe3
    for i, byte in enumerate(raw):
        if byte == 0xe3:
            print(f"\n⚠️  Byte 0xe3 encontrado na posição {i}")
            # Mostrar 50 bytes ao redor
            start = max(0, i-25)
            end = min(len(raw), i+26)
            context = raw[start:end]
            print(f"Contexto (latin-1): {context.decode('latin-1')}")
            break
    else:
        print("✅ Nenhum byte 0xe3 encontrado")
        
except Exception as e:
    print(f"Erro ao ler .env: {e}")