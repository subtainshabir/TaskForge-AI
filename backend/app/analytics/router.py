from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.ai.base import AIProvider
from app.ai.factory import get_ai_provider
from app.ai.progress_insights.schemas import ProgressInsightsResponse
from app.analytics import service
from app.analytics.schemas import ProgressAnalyticsResponse
from app.auth.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/progress", response_model=ProgressAnalyticsResponse)
def get_progress_analytics(
    project_id: Optional[int] = Query(default=None, description="Optional project ID filter"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ProgressAnalyticsResponse:
    """
    Get progress analytics for the authenticated user's workspace or a specific project.
    """
    return service.get_progress_analytics(
        db=db,
        user_id=current_user.id,
        project_id=project_id,
    )


@router.post("/progress/insights", response_model=ProgressInsightsResponse)
def get_progress_insights(
    project_id: Optional[int] = Query(default=None, description="Optional project ID filter"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    ai_provider: AIProvider = Depends(get_ai_provider),
) -> ProgressInsightsResponse:
    """
    Generate evidence-based AI progress insights for workspace or project.
    """
    return service.get_progress_insights(
        db=db,
        user_id=current_user.id,
        project_id=project_id,
        provider=ai_provider,
    )

