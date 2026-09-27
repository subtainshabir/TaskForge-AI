from typing import List, Literal, Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.db.session import get_db
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
