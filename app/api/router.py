from fastapi import APIRouter
from .law_firms.routes import router as law_firms_router
from .users.routes import router as users_router
from .clients.routes import router as clients_router
from .cases.routes import router as cases_router
from .tasks.routes import router as tasks_router
from .auth.routes import router as auth_router  # <-- ADICIONE ESTA LINHA

api_router = APIRouter()

api_router.include_router(law_firms_router, prefix="/law_firms", tags=["law-firms"])
api_router.include_router(users_router, prefix="/users", tags=["users"])
api_router.include_router(clients_router, prefix="/clients", tags=["clients"])
api_router.include_router(cases_router, prefix="/cases", tags=["cases"])
api_router.include_router(tasks_router, prefix="/tasks", tags=["tasks"])

# CORREÇÃO: incluir auth_router com prefixo "/auth"
api_router.include_router(auth_router, prefix="/auth", tags=["auth"])