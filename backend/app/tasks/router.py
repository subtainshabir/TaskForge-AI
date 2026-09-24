from typing import List, Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.ai.base import AIProvider
from app.ai.factory import get_ai_provider
from app.ai.phase_refinement.schemas import ApplyRefinementsRequest, PhaseRefinementResponse
from app.ai.task_understanding.schemas import TaskAnalysisResponse
from app.ai.task_understanding.service import analyze_task_understanding
from app.auth.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.projects.service import get_owned_project
from app.tasks import service
from app.tasks.schemas import (
    PhaseCreate,
    PhaseResponse,
    PhaseUpdate,
    PhasesGenerateRequest,
    TaskActivityResponse,
    TaskCreate,
    TaskDependencyCreate,
    TaskDependencyResponse,
    TaskResponse,
    TaskUpdate,
)

router = APIRouter(tags=["tasks"])


@router.get("/tasks", response_model=List[TaskResponse])
def list_tasks_global(
    search: Optional[str] = Query(default=None),
    project_id: Optional[int] = Query(default=None),
    status: Optional[str] = Query(default=None),
    priority: Optional[str] = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[TaskResponse]:
    return service.list_user_tasks(
        db,
        user_id=current_user.id,
        search=search,
        project_id=project_id,
        status_filter=status,
        priority_filter=priority,
    )


@router.post(
    "/projects/{project_id}/tasks", response_model=TaskResponse, status_code=status.HTTP_201_CREATED
)
def create_task(
    project_id: int,
    payload: TaskCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TaskResponse:
    project = get_owned_project(db, current_user.id, project_id)
    return service.create_task(db, project, current_user.id, payload)


@router.get("/projects/{project_id}/tasks", response_model=List[TaskResponse])
def list_project_tasks(
    project_id: int,
    search: Optional[str] = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[TaskResponse]:
    get_owned_project(db, current_user.id, project_id)
    return service.list_tasks(db, project_id, search=search)


@router.get("/tasks/{task_id}", response_model=TaskResponse)
def get_task(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TaskResponse:
    return service.get_owned_task(db, current_user.id, task_id)


@router.patch("/tasks/{task_id}", response_model=TaskResponse)
def update_task(
    task_id: int,
    payload: TaskUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TaskResponse:
    task = service.get_owned_task(db, current_user.id, task_id)
    return service.update_task(db, task, payload, user_id=current_user.id)


@router.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    task = service.get_owned_task(db, current_user.id, task_id)
    service.delete_task(db, task)


@router.post(
    "/tasks/{task_id}/dependencies",
    response_model=TaskDependencyResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_dependency(
    task_id: int,
    payload: TaskDependencyCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TaskDependencyResponse:
    return service.create_dependency(db, current_user.id, task_id, payload)


@router.get("/tasks/{task_id}/dependencies", response_model=List[TaskDependencyResponse])
def get_dependencies(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[TaskDependencyResponse]:
    return service.get_task_dependencies(db, current_user.id, task_id)


@router.delete(
    "/tasks/{task_id}/dependencies/{dependency_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_dependency(
    task_id: int,
    dependency_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    service.delete_dependency(db, current_user.id, task_id, dependency_id)


@router.get("/tasks/{task_id}/activities", response_model=List[TaskActivityResponse])
def get_task_activities(
    task_id: int,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[TaskActivityResponse]:
    return service.list_task_activities(db, current_user.id, task_id, page=page, limit=limit)


@router.post(
    "/tasks/{task_id}/ai/analyze",
    response_model=TaskAnalysisResponse,
)
def analyze_task_ai(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    ai_provider: AIProvider = Depends(get_ai_provider),
) -> TaskAnalysisResponse:
    task = service.get_owned_task(db, current_user.id, task_id)
    return analyze_task_understanding(task, ai_provider)


@router.get("/tasks/{task_id}/phases", response_model=List[PhaseResponse])
def get_task_phases(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[PhaseResponse]:
    return service.get_task_phases(db, current_user.id, task_id)


@router.post(
    "/tasks/{task_id}/phases",
    response_model=PhaseResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_phase(
    task_id: int,
    payload: PhaseCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PhaseResponse:
    return service.create_phase(db, current_user.id, task_id, payload)


@router.patch("/tasks/{task_id}/phases/{phase_id}", response_model=PhaseResponse)
def update_phase(
    task_id: int,
    phase_id: int,
    payload: PhaseUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PhaseResponse:
    return service.update_phase(db, current_user.id, task_id, phase_id, payload)


@router.delete(
    "/tasks/{task_id}/phases/{phase_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_phase(
    task_id: int,
    phase_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    service.delete_phase(db, current_user.id, task_id, phase_id)


@router.post("/tasks/{task_id}/phases/generate", response_model=List[PhaseResponse])
def generate_phases(
    task_id: int,
    payload: Optional[PhasesGenerateRequest] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    ai_provider: AIProvider = Depends(get_ai_provider),
) -> List[PhaseResponse]:
    replace_existing = payload.replace_existing if payload else False
    return service.generate_task_phases(
        db, current_user.id, task_id, ai_provider, replace_existing=replace_existing
    )


@router.post("/tasks/{task_id}/phases/refine", response_model=PhaseRefinementResponse)
def refine_phases(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    ai_provider: AIProvider = Depends(get_ai_provider),
) -> PhaseRefinementResponse:
    return service.refine_task_phases(
        db=db, user_id=current_user.id, task_id=task_id, provider=ai_provider
    )


@router.post("/tasks/{task_id}/phases/refine/apply", response_model=List[PhaseResponse])
def apply_refinements(
    task_id: int,
    payload: ApplyRefinementsRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[PhaseResponse]:
    return service.apply_phase_refinements(
        db=db, user_id=current_user.id, task_id=task_id, suggestions=payload.suggestions
    )


@router.post("/tasks/{task_id}/phases/apply-refinements", response_model=List[PhaseResponse])
def apply_refinements_alias(
    task_id: int,
    payload: ApplyRefinementsRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[PhaseResponse]:
    return service.apply_phase_refinements(
        db=db, user_id=current_user.id, task_id=task_id, suggestions=payload.suggestions
    )