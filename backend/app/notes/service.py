from typing import List, Optional

from fastapi import HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload

from app.models.note import Note
from app.models.project import Project
from app.models.task import Task
from app.notes.schemas import NoteCreate, NoteUpdate
from app.projects.service import get_owned_project
from app.tasks.service import get_owned_task


def create_note(db: Session, user_id: int, payload: NoteCreate) -> Note:
    """
    Create a new note with validated ownership and project/task relationships.
    """
    project_id = payload.project_id

    # Validate project ownership if project_id is provided
    if project_id is not None:
        get_owned_project(db, user_id, project_id)

    # Validate task ownership and relationship if task_id is provided
    if payload.task_id is not None:
        task = get_owned_task(db, user_id, payload.task_id)

        # If project_id was also specified, it must match task.project_id
        if project_id is not None and task.project_id != project_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Task does not belong to the specified project",
            )
        # If project_id was not specified, inherit task's project_id
        if project_id is None:
            project_id = task.project_id

    note = Note(
        user_id=user_id,
        project_id=project_id,
        task_id=payload.task_id,
        title=payload.title,
        content=payload.content,
    )
    db.add(note)
    db.commit()
    db.refresh(note)
    return note


def get_owned_note(db: Session, user_id: int, note_id: int) -> Note:
    """
    Retrieve a note owned by user_id or raise 404.
    """
    note = (
        db.execute(
            select(Note)
            .where(Note.id == note_id, Note.user_id == user_id)
            .options(selectinload(Note.project), selectinload(Note.task))
        )
        .scalar_one_or_none()
    )
    if note is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Note not found",
        )
    return note


def list_notes(
    db: Session,
    user_id: int,
    project_id: Optional[int] = None,
    task_id: Optional[int] = None,
    general_only: bool = False,
    search: Optional[str] = None,
    sort_by: str = "updated_at",
    order: str = "desc",
) -> List[Note]:
    """
    List notes belonging to user_id with optional project, task, and keyword filters.
    """
    if project_id is not None:
        get_owned_project(db, user_id, project_id)

    if task_id is not None:
        get_owned_task(db, user_id, task_id)

    query = (
        select(Note)
        .where(Note.user_id == user_id)
        .options(selectinload(Note.project), selectinload(Note.task))
    )

    if project_id is not None:
        query = query.where(Note.project_id == project_id)

    if task_id is not None:
        query = query.where(Note.task_id == task_id)

    if general_only:
        query = query.where(Note.project_id.is_(None), Note.task_id.is_(None))

    if search:
        search_pattern = f"%{search.strip()}%"
        query = query.where(
            or_(
                Note.title.ilike(search_pattern),
                Note.content.ilike(search_pattern),
            )
        )

    # Column ordering
    if sort_by == "created_at":
        col = Note.created_at
    elif sort_by == "title":
        col = Note.title
    else:
        col = Note.updated_at

    col = col.desc() if order == "desc" else col.asc()
    query = query.order_by(col)

    return list(db.execute(query).scalars().all())


def update_note(db: Session, note: Note, payload: NoteUpdate) -> Note:
    """
    Update note title and/or content. Associations remain immutable.
    """
    if payload.title is not None:
        note.title = payload.title
    if payload.content is not None:
        note.content = payload.content

    db.commit()
    db.refresh(note)
    return note


def delete_note(db: Session, note: Note) -> None:
    """
    Delete a note from the database.
    """
    db.delete(note)
    db.commit()


def list_project_notes(db: Session, user_id: int, project_id: int) -> List[Note]:
    """
    Retrieve all notes belonging to a specific project owned by the user.
    """
    get_owned_project(db, user_id, project_id)
    query = (
        select(Note)
        .where(Note.user_id == user_id, Note.project_id == project_id)
        .options(selectinload(Note.project), selectinload(Note.task))
        .order_by(Note.updated_at.desc())
    )
    return list(db.execute(query).scalars().all())


def list_task_notes(db: Session, user_id: int, task_id: int) -> List[Note]:
    """
    Retrieve all notes belonging to a specific task owned by the user.
    """
    get_owned_task(db, user_id, task_id)
    query = (
        select(Note)
        .where(Note.user_id == user_id, Note.task_id == task_id)
        .options(selectinload(Note.project), selectinload(Note.task))
        .order_by(Note.updated_at.desc())
    )
    return list(db.execute(query).scalars().all())
