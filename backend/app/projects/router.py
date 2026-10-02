from typing import List, Literal, Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.ai.base import AIProvider
from app.ai.factory import get_ai_provider
from app.ai.project_intelligence.schemas import ProjectProgressIntelligenceResponse
from app.ai.project_knowledge.schemas import ProjectAIRequest, ProjectAIResponse
from app.ai.project_knowledge.service import answer_project_question_ai
from app.auth.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.notes import service as notes_service
from app.notes.schemas import NoteResponse
from app.projects import service
from app.projects.schemas import (
    ProjectCreate,
    ProjectResponse,
    ProjectStatusLiteral,
    ProjectUpdate,
)

router = APIRouter(prefix="/projects", tags=["projects"])


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
def create_project(
    payload: ProjectCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ProjectResponse:
    return service.create_project(db, current_user.id, payload)


@router.get("", response_model=List[ProjectResponse])
def list_projects(
    status_filter: Optional[ProjectStatusLiteral] = Query(default=None, alias="status"),
    sort_by: Literal["created_at", "updated_at"] = Query(default="created_at"),
    order: Literal["asc", "desc"] = Query(default="desc"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[ProjectResponse]:
    return service.list_projects(
        db, current_user.id, status_filter=status_filter, sort_by=sort_by, order=order
    )


@router.get("/{project_id}", response_model=ProjectResponse)
def get_project(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ProjectResponse:
    return service.get_owned_project(db, current_user.id, project_id)


@router.patch("/{project_id}", response_model=ProjectResponse)
def update_project(
    project_id: int,
    payload: ProjectUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ProjectResponse:
    project = service.get_owned_project(db, current_user.id, project_id)
    return service.update_project(db, project, payload)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    project = service.get_owned_project(db, current_user.id, project_id)
    service.delete_project(db, project)


@router.post(
    "/{project_id}/ai/progress-insights",
    response_model=ProjectProgressIntelligenceResponse,
)
def get_project_progress_intelligence_endpoint(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    ai_provider: AIProvider = Depends(get_ai_provider),
) -> ProjectProgressIntelligenceResponse:
    """
    Generate evidence-based AI Project Progress Intelligence for a specific project.
    """
    return service.get_project_progress_intelligence(
        db=db,
        user_id=current_user.id,
        project_id=project_id,
        provider=ai_provider,
    )


@router.post(
    "/{project_id}/ai/progress-intelligence",
    response_model=ProjectProgressIntelligenceResponse,
    include_in_schema=False,
)
def get_project_progress_intelligence_alias(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    ai_provider: AIProvider = Depends(get_ai_provider),
) -> ProjectProgressIntelligenceResponse:
    return service.get_project_progress_intelligence(
        db=db,
        user_id=current_user.id,
        project_id=project_id,
        provider=ai_provider,
    )


@router.get("/{project_id}/notes", response_model=List[NoteResponse])
def get_project_notes_endpoint(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[NoteResponse]:
    """
    Get all notes belonging to a specific project owned by the authenticated user.
    """
    return notes_service.list_project_notes(
        db=db, user_id=current_user.id, project_id=project_id
    )


@router.post(
    "/{project_id}/ai/ask",
    response_model=ProjectAIResponse,
)
def ask_project_ai_endpoint(
    project_id: int,
    payload: ProjectAIRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    ai_provider: AIProvider = Depends(get_ai_provider),
) -> ProjectAIResponse:
    """
    Ask an AI question about an individual project using its tasks, phases, notes, and progress.
    Answers are derived strictly from the project's data.
    Does NOT modify any project data.
    """
    return answer_project_question_ai(
        db=db,
        user_id=current_user.id,
        project_id=project_id,
        question=payload.question,
        conversation_history=payload.conversation_history,
        provider=ai_provider,
    )