import asyncio
from app.database import AsyncSessionLocal
from app import models
from app.core.security import get_password_hash
import uuid

async def seed():
    async with AsyncSessionLocal() as db:
        try:
            # Criar Escritório
            firm_id = uuid.uuid4()
            firm = models.LawFirm(
                id=firm_id,
                name="Escritorio Principal",
                cnpj="00.000.000/0001-00",
                email="contato@escritorio.com"
            )
            db.add(firm)
            
            # Criar Usuário
            user = models.User(
                id=uuid.uuid4(),
                name="Administrador",
                email="admin@escritorio.com",
                password_hash=get_password_hash("senha123"),
                role="admin",
                law_firm_id=firm_id,
                is_active=True
            )
            db.add(user)
            
            await db.commit()
            print("Sucesso: Escritório e Usuário (admin@escritorio.com / senha123) criados!")
        except Exception as e:
            await db.rollback()
            print(f"Erro ao criar dados: {e}")

if __name__ == "__main__":
    asyncio.run(seed())
