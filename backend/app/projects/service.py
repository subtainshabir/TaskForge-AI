from typing import List, Optional

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.enums import ProjectStatus
from app.models.project import Project
from app.projects.schemas import ProjectCreate, ProjectUpdate


def list_projects(
    db: Session,
    user_id: int,
    status_filter: Optional[str] = None,
    sort_by: str = "created_at",
    order: str = "desc",
) -> List[Project]:
    column = Project.updated_at if sort_by == "updated_at" else Project.created_at
    column = column.desc() if order == "desc" else column.asc()

    query = select(Project).where(Project.user_id == user_id)
    if status_filter is not None:
        query = query.where(Project.status == ProjectStatus(status_filter))
    query = query.order_by(column)

    return list(db.execute(query).scalars().all())


def get_owned_project(db: Session, user_id: int, project_id: int) -> Project:
    project = db.execute(
        select(Project).where(Project.id == project_id, Project.user_id == user_id)
    ).scalar_one_or_none()
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return project


def create_project(db: Session, user_id: int, payload: ProjectCreate) -> Project:
    project = Project(
        user_id=user_id,
        name=payload.name,
        description=payload.description,
        status=ProjectStatus(payload.status),
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


def update_project(db: Session, project: Project, payload: ProjectUpdate) -> Project:
    if payload.name is not None:
        project.name = payload.name
    if payload.description is not None:
        project.description = payload.description
    if payload.status is not None:
        project.status = ProjectStatus(payload.status)
    db.commit()
    db.refresh(project)
    return project


def delete_project(db: Session, project: Project) -> None:
    db.delete(project)
    db.commit()