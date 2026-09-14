from fastapi import APIRouter

from app.api import health

api_router = APIRouter()
api_router.include_router(health.router)

# Future routers (tasks, projects, notes, chat, agent, etc.) are
# registered here in later phases.