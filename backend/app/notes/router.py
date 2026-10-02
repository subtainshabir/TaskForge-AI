from typing import List, Literal, Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from sqlalchemy import select

from app.ai.base import AIProvider
from app.ai.factory import get_ai_provider
from app.ai.note_summarization.schemas import NoteSummaryResponse
from app.ai.note_summarization.service import summarize_note_ai
from app.ai.note_extraction.schemas import NoteExtractionResponse
from app.ai.note_extraction.service import extract_note_ai
from app.ai.note_task_suggestions.schemas import TaskSuggestionResponse
from app.ai.note_task_suggestions.service import suggest_tasks_from_note_ai
from app.ai.note_improvement.schemas import NoteImprovementResponse
from app.ai.note_improvement.service import improve_note_ai
from app.ai.note_qa.schemas import NoteQARequest, NoteQAResponse
from app.ai.note_qa.service import answer_note_question_ai
from app.auth.dependencies import get_current_user
from app.db.session import get_db
from app.models.task import Task
from app.models.user import User
from app.notes import service
from app.notes.schemas import NoteCreate, NoteResponse, NoteUpdate

router = APIRouter(prefix="/notes", tags=["notes"])


@router.post("", response_model=NoteResponse, status_code=status.HTTP_201_CREATED)
def create_note_endpoint(
    payload: NoteCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> NoteResponse:
    """
    Create a new note for the authenticated user, optionally associated with a project or task.
    """
    return service.create_note(db=db, user_id=current_user.id, payload=payload)


@router.get("", response_model=List[NoteResponse])
def list_notes_endpoint(
    project_id: Optional[int] = Query(default=None, description="Filter by project ID"),
    task_id: Optional[int] = Query(default=None, description="Filter by task ID"),
    general_only: bool = Query(default=False, description="Filter only general notes without project or task"),
    search: Optional[str] = Query(default=None, description="Search in note title or content"),
    sort_by: Literal["updated_at", "created_at", "title"] = Query(default="updated_at"),
    order: Literal["asc", "desc"] = Query(default="desc"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[NoteResponse]:
    """
    List all notes for the authenticated user with optional filtering.
    """
    # Normalize parameters if invoked directly in python tests
    p_id = project_id if isinstance(project_id, int) else None
    t_id = task_id if isinstance(task_id, int) else None
    g_only = general_only if isinstance(general_only, bool) else False
    s_query = search if isinstance(search, str) else None
    s_by = sort_by if isinstance(sort_by, str) and not hasattr(sort_by, "default") else "updated_at"
    s_order = order if isinstance(order, str) and not hasattr(order, "default") else "desc"

    return service.list_notes(
        db=db,
        user_id=current_user.id,
        project_id=p_id,
        task_id=t_id,
        general_only=g_only,
        search=s_query,
        sort_by=s_by,
        order=s_order,
    )


@router.get("/{note_id}", response_model=NoteResponse)
def get_note_endpoint(
    note_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> NoteResponse:
    """
    Get a single note by ID for the authenticated user.
    """
    return service.get_owned_note(db=db, user_id=current_user.id, note_id=note_id)


@router.patch("/{note_id}", response_model=NoteResponse)
def update_note_endpoint(
    note_id: int,
    payload: NoteUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> NoteResponse:
    """
    Update a note's title or content.
    """
    note = service.get_owned_note(db=db, user_id=current_user.id, note_id=note_id)
    return service.update_note(db=db, note=note, payload=payload)


@router.delete("/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_note_endpoint(
    note_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    """
    Delete a note owned by the authenticated user.
    """
    note = service.get_owned_note(db=db, user_id=current_user.id, note_id=note_id)
    service.delete_note(db=db, note=note)


@router.post("/{note_id}/ai/summarize", response_model=NoteSummaryResponse)
def summarize_note_endpoint(
    note_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    ai_provider: AIProvider = Depends(get_ai_provider),
) -> NoteSummaryResponse:
    """
    Generate an evidence-based, structured AI summary of an existing note owned by the authenticated user.
    Does not modify the original note.
    """
    note = service.get_owned_note(db=db, user_id=current_user.id, note_id=note_id)
    return summarize_note_ai(
        title=note.title,
        content=note.content,
        provider=ai_provider,
    )


@router.post("/{note_id}/ai/extract", response_model=NoteExtractionResponse)
def extract_note_endpoint(
    note_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    ai_provider: AIProvider = Depends(get_ai_provider),
) -> NoteExtractionResponse:
    """
    Extract structured information (action items, decisions, facts, dates, people, tech terms, follow-ups)
    from an existing note owned by the authenticated user.
    Does not modify the original note or any other records.
    """
    note = service.get_owned_note(db=db, user_id=current_user.id, note_id=note_id)
    return extract_note_ai(
        title=note.title,
        content=note.content,
        provider=ai_provider,
    )


@router.post("/{note_id}/ai/task-suggestions", response_model=TaskSuggestionResponse)
def suggest_tasks_endpoint(
    note_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    ai_provider: AIProvider = Depends(get_ai_provider),
) -> TaskSuggestionResponse:
    """
    Analyze note content and suggest actionable task candidates for user review.
    Does not automatically create tasks or modify the original note.
    """
    note = service.get_owned_note(db=db, user_id=current_user.id, note_id=note_id)

    # Determine project context:
    # If the note belongs to a project (and not directly a task), default to that project.
    # If the note belongs to a task, do NOT automatically assign project (user chooses).
    # If general note, project is None.
    suggested_project_id = None
    suggested_project_name = None
    if note.project_id is not None and note.task_id is None:
        suggested_project_id = note.project_id
        suggested_project_name = note.project_name

    # Load relevant existing tasks for duplicate checking
    project_for_tasks = note.project_id
    if project_for_tasks is None and note.task is not None:
        project_for_tasks = note.task.project_id

    existing_task_titles: List[str] = []
    if project_for_tasks is not None:
        proj_tasks = db.execute(
            select(Task.title).where(Task.project_id == project_for_tasks)
        ).scalars().all()
        existing_task_titles.extend([t for t in proj_tasks if t])

    user_tasks = db.execute(
        select(Task.title).where(Task.user_id == current_user.id).limit(100)
    ).scalars().all()
    for ut in user_tasks:
        if ut and ut not in existing_task_titles:
            existing_task_titles.append(ut)

    return suggest_tasks_from_note_ai(
        title=note.title,
        content=note.content,
        provider=ai_provider,
        existing_tasks=existing_task_titles,
        project_id=suggested_project_id,
        project_name=suggested_project_name,
    )


@router.post("/{note_id}/ai/improve", response_model=NoteImprovementResponse)
def improve_note_endpoint(
    note_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    ai_provider: AIProvider = Depends(get_ai_provider),
) -> NoteImprovementResponse:
    """
    Review an existing note owned by the authenticated user and suggest improvements
    to clarity, structure, grammar, conciseness, and organization.
    Does NOT modify the note in the database.
    """
    note = service.get_owned_note(db=db, user_id=current_user.id, note_id=note_id)
    return improve_note_ai(
        title=note.title,
        content=note.content,
        provider=ai_provider,
    )


@router.post("/{note_id}/ai/ask", response_model=NoteQAResponse)
def ask_note_question_endpoint(
    note_id: int,
    payload: NoteQARequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    ai_provider: AIProvider = Depends(get_ai_provider),
) -> NoteQAResponse:
    """
    Ask a question about an individual note owned by the authenticated user.
    Answers are derived strictly from the note's content.
    Does NOT modify the note in the database.
    """
    note = service.get_owned_note(db=db, user_id=current_user.id, note_id=note_id)
    return answer_note_question_ai(
        title=note.title,
        content=note.content,
        question=payload.question,
        conversation_history=payload.conversation_history,
        provider=ai_provider,
    )




