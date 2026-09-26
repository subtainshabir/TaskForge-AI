from fastapi import APIRouter

from app.api import health
from app.auth.router import router as auth_router
from app.users.router import router as users_router
from app.projects.router import router as projects_router
from app.tasks.router import router as tasks_router
from app.analytics.router import router as analytics_router

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth_router)
api_router.include_router(users_router)
api_router.include_router(projects_router)
api_router.include_router(tasks_router)
api_router.include_router(analytics_router)

# Future routers (notes, chat, agent, etc.) are
# registered here in later phases.