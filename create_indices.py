
import asyncio
from sqlalchemy import text
from app.database import engine

async def create_indices():
    print("Iniciando criacao manual de indices...")
    
    indices_to_create = [
        "CREATE INDEX IF NOT EXISTS idx_clients_law_firm_id ON clients (law_firm_id);",
        "CREATE INDEX IF NOT EXISTS idx_clients_law_firm_document ON clients (law_firm_id, document);",
        "CREATE INDEX IF NOT EXISTS idx_users_law_firm_id ON users (law_firm_id);",
        "CREATE INDEX IF NOT EXISTS idx_tasks_law_firm_id ON tasks (law_firm_id);",
        "DROP INDEX IF EXISTS idx_client_document;"
    ]
    
    async with engine.begin() as conn:
        for query in indices_to_create:
            try:
                print(f"Executando: {query}")
                await conn.execute(text(query))
                print("Sucesso!")
            except Exception as e:
                print(f"Erro ao criar indice: {e}")
                
    print("\nTodos os indices foram processados!")

if __name__ == "__main__":
    asyncio.run(create_indices())
