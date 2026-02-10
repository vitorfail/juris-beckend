import psycopg2
from urllib.parse import quote, quote_plus
import socket

# Seus dados
config = {
    "host": "dpg-d64h2ff5r7bs73afur9g-a",
    "port": "5432",
    "user": "juris_user",
    "password": "rHgrDAbCAVRFu2sUWAiPSBopBr40wS3F",
    "database": "juris"
}

print("🔍 Analisando o HOSTNAME...")
print(f"Host: {config['host']}")
print(f"Tamanho: {len(config['host'])} caracteres")
print("Caracteres do hostname:")
for i, char in enumerate(config['host']):
    print(f"  Pos {i:2d}: '{char}' - ASCII: {ord(char)}")

print("\n🔍 Testando resolução DNS...")
try:
    ip = socket.gethostbyname(config['host'])
    print(f"✅ Host resolve para IP: {ip}")
except Exception as e:
    print(f"❌ Não consegui resolver host: {e}")

print("\n🔍 Testando com host IP diretamente (se conseguir resolver)...")