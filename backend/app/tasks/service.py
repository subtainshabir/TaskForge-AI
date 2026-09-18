from typing import List

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.enums import TaskPriority, WorkStatus
from app.models.project import Project
from app.models.task import Task
from app.tasks.schemas import TaskCreate, TaskUpdate


def list_tasks(db: Session, project_id: int) -> List[Task]:
    query = select(Task).where(Task.project_id == project_id).order_by(Task.created_at.desc())
    return list(db.execute(query).scalars().all())


def get_owned_task(db: Session, user_id: int, task_id: int) -> Task:
    task = db.execute(
        select(Task)
        .join(Project, Task.project_id == Project.id)
        .where(Task.id == task_id, Project.user_id == user_id)
    ).scalar_one_or_none()
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    return task


def create_task(db: Session, project: Project, user_id: int, payload: TaskCreate) -> Task:
    task = Task(
        project_id=project.id,
        user_id=user_id,
        title=payload.title,
        description=payload.description,
        status=WorkStatus(payload.status),
        priority=TaskPriority(payload.priority),
        deadline=payload.deadline,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


def update_task(db: Session, task: Task, payload: TaskUpdate) -> Task:
    if payload.title is not None:
        task.title = payload.title
    if payload.description is not None:
        task.description = payload.description
    if payload.status is not None:
        task.status = WorkStatus(payload.status)
    if payload.priority is not None:
        task.priority = TaskPriority(payload.priority)
    if payload.deadline is not None:
        task.deadline = payload.deadline
    db.commit()
    db.refresh(task)
    return task


def delete_task(db: Session, task: Task) -> None:
    db.delete(task)
    db.commit()