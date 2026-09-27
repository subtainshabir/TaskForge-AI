from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.ai.base import AIProvider
from app.ai.factory import get_ai_provider
from app.ai.project_intelligence.schemas import (
    ProjectProgressInsight,
    ProjectProgressIntelligenceResponse,
)
from app.ai.project_intelligence.service import generate_project_progress_intelligence_ai
from app.models.enums import ProjectStatus, TaskPriority, WorkStatus
from app.models.project import Project
from app.models.task import Task
from app.projects.schemas import ProjectCreate, ProjectUpdate
from app.tasks.service import calculate_phases_progress


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


def get_project_progress_intelligence(
    db: Session,
    user_id: int,
    project_id: int,
    provider: Optional[AIProvider] = None,
) -> ProjectProgressIntelligenceResponse:
    """
    Generate evidence-based AI Project Progress Intelligence for a project owned by user_id.
    Uses selectinload to prevent N+1 queries.
    Task progress is derived directly from phases using calculate_phases_progress.
    """
    project = get_owned_project(db, user_id, project_id)

    if provider is None:
        provider = get_ai_provider()

    stmt = (
        select(Task)
        .where(Task.project_id == project_id, Task.user_id == user_id)
        .options(selectinload(Task.phases), selectinload(Task.dependencies))
    )
    tasks = list(db.execute(stmt).scalars().all())

    # Empty state: Return clean response if project has 0 tasks
    if len(tasks) == 0:
        return ProjectProgressIntelligenceResponse(
            project_summary="No project progress data available yet. Add tasks to generate project intelligence.",
            overall_progress=0,
            insights=[],
        )

    now_utc = datetime.now(timezone.utc)
    completed_tasks = 0
    in_progress_tasks = 0
    todo_tasks = 0
    blocked_tasks = 0
    cancelled_tasks = 0
    total_progress_sum = 0

    high_priority_incomplete = []
    stalled_tasks = []
    overdue_tasks = []
    upcoming_deadline_tasks = []
    low_progress_active_tasks = []
    tasks_summary = []

    for t in tasks:
        prog = calculate_phases_progress(t.phases)
        total_progress_sum += prog

        s = t.status.value if hasattr(t.status, "value") else str(t.status)
        p = t.priority.value if hasattr(t.priority, "value") else str(t.priority)

        if s in (WorkStatus.COMPLETED.value, "completed"):
            completed_tasks += 1
        elif s in (WorkStatus.IN_PROGRESS.value, "in_progress"):
            in_progress_tasks += 1
        elif s in (WorkStatus.TODO.value, "todo"):
            todo_tasks += 1
        elif s in (WorkStatus.BLOCKED.value, "blocked"):
            blocked_tasks += 1
        elif s in (WorkStatus.CANCELLED.value, "cancelled"):
            cancelled_tasks += 1

        # Check if stalled (in_progress with progress < 25%)
        if s in (WorkStatus.IN_PROGRESS.value, "in_progress") and prog < 25:
            stalled_tasks.append({
                "title": t.title,
                "progress": prog,
                "priority": p,
                "status": s,
            })

        # Low progress active (in_progress with progress < 50%)
        if s in (WorkStatus.IN_PROGRESS.value, "in_progress") and prog < 50:
            low_progress_active_tasks.append({
                "title": t.title,
                "progress": prog,
                "priority": p,
                "status": s,
            })

        # High-priority incomplete
        if (
            p in (TaskPriority.HIGH.value, TaskPriority.URGENT.value, "high", "urgent")
            and s not in (WorkStatus.COMPLETED.value, "completed")
        ):
            high_priority_incomplete.append({
                "title": t.title,
                "progress": prog,
                "priority": p,
                "status": s,
            })

        # Deadlines
        if t.deadline and s not in (WorkStatus.COMPLETED.value, "completed"):
            deadline_tz = t.deadline
            if deadline_tz.tzinfo is None:
                deadline_tz = deadline_tz.replace(tzinfo=timezone.utc)
            if deadline_tz < now_utc:
                overdue_tasks.append({
                    "title": t.title,
                    "progress": prog,
                    "deadline": deadline_tz.strftime("%Y-%m-%d"),
                    "priority": p,
                    "status": s,
                })
            elif deadline_tz <= now_utc + timedelta(days=7):
                upcoming_deadline_tasks.append({
                    "title": t.title,
                    "progress": prog,
                    "deadline": deadline_tz.strftime("%Y-%m-%d"),
                    "priority": p,
                    "status": s,
                })

        tasks_summary.append({
            "title": t.title,
            "status": s,
            "priority": p,
            "progress": prog,
            "deadline": t.deadline.strftime("%Y-%m-%d") if t.deadline else None,
            "phases_count": len(t.phases) if t.phases else 0,
            "dependencies_count": len(t.dependencies) if t.dependencies else 0,
        })

    total_tasks = len(tasks)
    avg_progress = int(round(total_progress_sum / total_tasks)) if total_tasks > 0 else 0

    stats = {
        "total_tasks": total_tasks,
        "completed_tasks": completed_tasks,
        "in_progress_tasks": in_progress_tasks,
        "todo_tasks": todo_tasks,
        "blocked_tasks": blocked_tasks,
        "cancelled_tasks": cancelled_tasks,
        "average_task_progress": avg_progress,
        "average_progress": avg_progress,
    }

    workload_summary = [
        f"{completed_tasks} of {total_tasks} tasks completed ({int(round(completed_tasks/total_tasks*100))}%)" if total_tasks else "0 completed",
        f"{in_progress_tasks} in-progress tasks",
        f"{todo_tasks} to-do (not started) tasks",
    ]
    if blocked_tasks > 0:
        workload_summary.append(f"{blocked_tasks} blocked tasks")

    project_info = {
        "name": project.name,
        "description": project.description,
        "status": project.status.value if hasattr(project.status, "value") else str(project.status),
    }

    task_breakdown = {
        "high_priority_incomplete": high_priority_incomplete,
        "stalled_tasks": stalled_tasks,
        "overdue_tasks": overdue_tasks,
        "upcoming_deadline_tasks": upcoming_deadline_tasks,
        "low_progress_active_tasks": low_progress_active_tasks,
        "workload_summary": workload_summary,
        "tasks_summary": tasks_summary,
    }

    return generate_project_progress_intelligence_ai(
        project_info=project_info,
        stats=stats,
        task_breakdown=task_breakdown,
        provider=provider,
    )