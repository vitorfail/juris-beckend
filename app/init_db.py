import logging
from sqlalchemy.orm import Session
from .database import SessionLocal, engine
from . import models
from .core.security import get_password_hash

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def init_db() -> None:
    """
    Inicializa o banco de dados com dados padrão.
    """
    try:
        # Criar todas as tabelas
        models.Base.metadata.create_all(bind=engine)
        
        db = SessionLocal()
        
        # Verificar se já existe algum escritório
        existing_firm = db.query(models.LawFirm).first()
        
        if not existing_firm:
            logger.info("Criando dados iniciais...")
            
            # Criar escritório padrão
            law_firm = models.LawFirm(
                name="Escritório Modelo Advocacia",
                cnpj="12.345.678/0001-90",
                email="contato@escritoriomodelo.com",
                phone="(11) 99999-9999"
            )
            db.add(law_firm)
            db.commit()
            db.refresh(law_firm)
            
            # Criar usuário admin padrão
            admin_user = models.User(
                law_firm_id=law_firm.id,
                name="Administrador",
                email="admin@escritorio.com",
                password_hash=get_password_hash("admin123"),
                role="admin",
                is_active=True
            )
            db.add(admin_user)
            
            # Criar usuário advogado exemplo
            lawyer_user = models.User(
                law_firm_id=law_firm.id,
                name="Dr. João Advogado",
                email="joao@escritorio.com",
                password_hash=get_password_hash("advogado123"),
                role="lawyer",
                is_active=True
            )
            db.add(lawyer_user)
            
            # Criar cliente exemplo
            client = models.Client(
                law_firm_id=law_firm.id,
                type="pf",
                name="Maria Silva",
                document="123.456.789-00",
                email="maria@email.com",
                phone="(11) 98888-7777",
                address="Rua Exemplo, 123 - São Paulo/SP"
            )
            db.add(client)
            
            db.commit()
            logger.info("Dados iniciais criados com sucesso!")
            
            # Criar processo exemplo
            case = models.Case(
                law_firm_id=law_firm.id,
                client_id=client.id,
                case_number="1234567-89.2023.8.26.0000",
                court="1ª Vara Cível",
                area="cível",
                status="em andamento",
                distribution_date="2023-01-15",
                value=50000.00,
                description="Ação de cobrança",
                responsible_lawyer_id=lawyer_user.id
            )
            db.add(case)
            db.commit()
            
            logger.info(f"Escritório criado: {law_firm.name}")
            logger.info(f"Usuário admin criado: {admin_user.email}")
            logger.info(f"Processo exemplo criado: {case.case_number}")
            
        else:
            logger.info("Banco de dados já inicializado")
            
    except Exception as e:
        logger.error(f"Erro ao inicializar banco de dados: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    init_db()