from fastapi import APIRouter

from app.api import health
from app.auth.router import router as auth_router

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth_router)

# Future routers (tasks, projects, notes, chat, agent, etc.) are
# registered here in later phases.