from typing import List, Optional

from fastapi import HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload

from app.models.enums import TaskPriority, WorkStatus
from app.models.project import Project
from app.models.task import Task
from app.models.task_dependency import TaskDependency
from app.tasks.schemas import TaskCreate, TaskDependencyCreate, TaskUpdate


def list_user_tasks(
    db: Session,
    user_id: int,
    search: Optional[str] = None,
    project_id: Optional[int] = None,
    status_filter: Optional[str] = None,
    priority_filter: Optional[str] = None,
) -> List[Task]:
    query = (
        select(Task)
        .join(Project, Task.project_id == Project.id)
        .where(Project.user_id == user_id)
        .options(
            selectinload(Task.project),
            selectinload(Task.dependencies).selectinload(TaskDependency.depends_on_task),
        )
    )

    if project_id is not None:
        query = query.where(Task.project_id == project_id)

    if status_filter:
        try:
            ws = WorkStatus(status_filter)
            query = query.where(Task.status == ws)
        except ValueError:
            pass

    if priority_filter:
        try:
            tp = TaskPriority(priority_filter)
            query = query.where(Task.priority == tp)
        except ValueError:
            pass

    term = (search or "").strip()
    if term:
        pattern = f"%{term}%"
        query = query.where(or_(Task.title.ilike(pattern), Task.description.ilike(pattern)))

    query = query.order_by(Task.created_at.desc())
    return list(db.execute(query).scalars().all())


def list_tasks(db: Session, project_id: int, search: Optional[str] = None) -> List[Task]:
    query = (
        select(Task)
        .where(Task.project_id == project_id)
        .options(
            selectinload(Task.project),
            selectinload(Task.dependencies).selectinload(TaskDependency.depends_on_task),
        )
    )

    term = (search or "").strip()
    if term:
        pattern = f"%{term}%"
        query = query.where(or_(Task.title.ilike(pattern), Task.description.ilike(pattern)))

    query = query.order_by(Task.created_at.desc())
    return list(db.execute(query).scalars().all())


def get_owned_task(db: Session, user_id: int, task_id: int) -> Task:
    task = db.execute(
        select(Task)
        .join(Project, Task.project_id == Project.id)
        .where(Task.id == task_id, Project.user_id == user_id)
        .options(
            selectinload(Task.project),
            selectinload(Task.dependencies).selectinload(TaskDependency.depends_on_task),
        )
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


def update_task(
    db: Session, task: Task, payload: TaskUpdate, user_id: Optional[int] = None
) -> Task:
    provided = payload.model_fields_set

    if payload.status is not None:
        task.status = WorkStatus(payload.status)

    if payload.priority is not None:
        task.priority = TaskPriority(payload.priority)

    if "deadline" in provided:
        task.deadline = payload.deadline

    if payload.title is not None:
        task.title = payload.title

    if "description" in provided:
        task.description = payload.description

    db.commit()
    db.refresh(task)
    return task


def delete_task(db: Session, task: Task) -> None:
    db.delete(task)
    db.commit()


def has_path_to_task(db: Session, from_task_id: int, target_task_id: int) -> bool:
    if from_task_id == target_task_id:
        return True
    visited = set()
    queue = [from_task_id]
    while queue:
        curr = queue.pop(0)
        if curr == target_task_id:
            return True
        if curr in visited:
            continue
        visited.add(curr)
        next_deps = db.execute(
            select(TaskDependency.depends_on_task_id).where(TaskDependency.task_id == curr)
        ).scalars().all()
        for dep_id in next_deps:
            if dep_id not in visited:
                queue.append(dep_id)
    return False


def create_dependency(
    db: Session, user_id: int, task_id: int, payload: TaskDependencyCreate
) -> TaskDependency:
    task = get_owned_task(db, user_id, task_id)
    dep_task_id = payload.depends_on_task_id

    if task_id == dep_task_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="A task cannot depend on itself"
        )

    dep_task = db.execute(select(Task).where(Task.id == dep_task_id)).scalar_one_or_none()
    if dep_task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Dependency task not found"
        )

    if dep_task.project_id != task.project_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A task can only depend on another task in the same project",
        )

    if dep_task.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access dependency task",
        )

    existing = db.execute(
        select(TaskDependency).where(
            TaskDependency.task_id == task_id,
            TaskDependency.depends_on_task_id == dep_task_id,
        )
    ).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This dependency already exists",
        )

    if has_path_to_task(db, dep_task_id, task_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Circular dependency detected",
        )

    dependency = TaskDependency(
        task_id=task_id,
        depends_on_task_id=dep_task_id,
    )
    db.add(dependency)
    db.commit()
    db.refresh(dependency)
    _ = dependency.depends_on_task
    return dependency


def get_task_dependencies(db: Session, user_id: int, task_id: int) -> List[TaskDependency]:
    get_owned_task(db, user_id, task_id)
    stmt = (
        select(TaskDependency)
        .where(TaskDependency.task_id == task_id)
        .options(selectinload(TaskDependency.depends_on_task))
        .order_by(TaskDependency.created_at.asc())
    )
    return list(db.execute(stmt).scalars().all())


def delete_dependency(db: Session, user_id: int, task_id: int, dependency_id: int) -> None:
    get_owned_task(db, user_id, task_id)
    dependency = db.execute(
        select(TaskDependency)
        .where(
            TaskDependency.id == dependency_id,
            TaskDependency.task_id == task_id,
        )
        .options(selectinload(TaskDependency.depends_on_task))
    ).scalar_one_or_none()
    if dependency is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Dependency not found"
        )

    db.delete(dependency)
    db.commit()