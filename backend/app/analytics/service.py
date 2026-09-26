from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.ai.base import AIProvider
from app.ai.factory import get_ai_provider
from app.ai.progress_insights.schemas import ProgressInsightsResponse
from app.ai.progress_insights.service import generate_progress_insights_ai
from app.analytics.schemas import (
    DistributionBucket,
    ProgressAnalyticsResponse,
    ProgressDistribution,
    ProjectProgressSummary,
    TaskOverview,
    TaskStatusBreakdown,
)
from app.models.enums import TaskPriority, WorkStatus
from app.models.project import Project
from app.models.task import Task
from app.tasks.service import calculate_phases_progress


def get_progress_analytics(
    db: Session,
    user_id: int,
    project_id: Optional[int] = None,
) -> ProgressAnalyticsResponse:
    """
    Compute progress analytics for an authenticated user's tasks and projects.
    Uses SQLAlchemy's selectinload to prevent N+1 queries.
    Task progress is derived directly from phases using calculate_phases_progress.
    """
    if project_id is not None:
        target_project = db.execute(
            select(Project).where(Project.id == project_id, Project.user_id == user_id)
        ).scalar_one_or_none()
        if not target_project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found",
            )

    task_query = (
        select(Task)
        .join(Project, Task.project_id == Project.id)
        .where(Project.user_id == user_id)
        .options(selectinload(Task.phases))
    )
    if project_id is not None:
        task_query = task_query.where(Task.project_id == project_id)

    tasks = list(db.execute(task_query).scalars().all())

    project_query = select(Project).where(Project.user_id == user_id)
    if project_id is not None:
        project_query = project_query.where(Project.id == project_id)

    projects = list(db.execute(project_query.order_by(Project.name.asc())).scalars().all())

    # Aggregations
    completed_tasks = 0
    in_progress_tasks = 0
    todo_tasks = 0
    blocked_tasks = 0
    cancelled_tasks = 0
    total_progress_sum = 0

    p0 = 0
    p1_24 = 0
    p25_49 = 0
    p50_74 = 0
    p75_99 = 0
    p100 = 0

    for t in tasks:
        prog = calculate_phases_progress(t.phases)
        total_progress_sum += prog

        # Status breakdown
        s = t.status.value if hasattr(t.status, "value") else str(t.status)
        if s == WorkStatus.COMPLETED.value or s == "completed":
            completed_tasks += 1
        elif s == WorkStatus.IN_PROGRESS.value or s == "in_progress":
            in_progress_tasks += 1
        elif s == WorkStatus.TODO.value or s == "todo":
            todo_tasks += 1
        elif s == WorkStatus.BLOCKED.value or s == "blocked":
            blocked_tasks += 1
        elif s == WorkStatus.CANCELLED.value or s == "cancelled":
            cancelled_tasks += 1

        # Progress distribution
        if prog == 0:
            p0 += 1
        elif 1 <= prog <= 24:
            p1_24 += 1
        elif 25 <= prog <= 49:
            p25_49 += 1
        elif 50 <= prog <= 74:
            p50_74 += 1
        elif 75 <= prog <= 99:
            p75_99 += 1
        elif prog >= 100:
            p100 += 1

    total_tasks = len(tasks)
    average_progress = int(round(total_progress_sum / total_tasks)) if total_tasks > 0 else 0

    overview = TaskOverview(
        total_tasks=total_tasks,
        completed_tasks=completed_tasks,
        in_progress_tasks=in_progress_tasks,
        todo_tasks=todo_tasks,
        blocked_tasks=blocked_tasks,
        cancelled_tasks=cancelled_tasks,
        average_progress=average_progress,
    )

    status_breakdown = TaskStatusBreakdown(
        completed=completed_tasks,
        in_progress=in_progress_tasks,
        todo=todo_tasks,
        blocked=blocked_tasks,
        cancelled=cancelled_tasks,
    )

    buckets = [
        DistributionBucket(
            key="0",
            label="0%",
            count=p0,
            percentage=int(round((p0 / total_tasks) * 100)) if total_tasks else 0,
        ),
        DistributionBucket(
            key="1_24",
            label="1–24%",
            count=p1_24,
            percentage=int(round((p1_24 / total_tasks) * 100)) if total_tasks else 0,
        ),
        DistributionBucket(
            key="25_49",
            label="25–49%",
            count=p25_49,
            percentage=int(round((p25_49 / total_tasks) * 100)) if total_tasks else 0,
        ),
        DistributionBucket(
            key="50_74",
            label="50–74%",
            count=p50_74,
            percentage=int(round((p50_74 / total_tasks) * 100)) if total_tasks else 0,
        ),
        DistributionBucket(
            key="75_99",
            label="75–99%",
            count=p75_99,
            percentage=int(round((p75_99 / total_tasks) * 100)) if total_tasks else 0,
        ),
        DistributionBucket(
            key="100",
            label="100%",
            count=p100,
            percentage=int(round((p100 / total_tasks) * 100)) if total_tasks else 0,
        ),
    ]

    progress_distribution = ProgressDistribution(
        zero=p0,
        low=p1_24 + p25_49,
        medium=p50_74,
        high=p75_99,
        complete=p100,
        p0=p0,
        p1_24=p1_24,
        p25_49=p25_49,
        p50_74=p50_74,
        p75_99=p75_99,
        p100=p100,
        buckets=buckets,
    )

    # Project-level calculations
    project_summaries = []
    for p in projects:
        p_tasks = [t for t in tasks if t.project_id == p.id]
        p_total = len(p_tasks)
        p_completed = sum(
            1
            for t in p_tasks
            if (t.status.value if hasattr(t.status, "value") else str(t.status))
            in (WorkStatus.COMPLETED.value, "completed")
        )
        p_in_progress = sum(
            1
            for t in p_tasks
            if (t.status.value if hasattr(t.status, "value") else str(t.status))
            in (WorkStatus.IN_PROGRESS.value, "in_progress")
        )
        p_todo = sum(
            1
            for t in p_tasks
            if (t.status.value if hasattr(t.status, "value") else str(t.status))
            in (WorkStatus.TODO.value, "todo")
        )
        p_blocked = sum(
            1
            for t in p_tasks
            if (t.status.value if hasattr(t.status, "value") else str(t.status))
            in (WorkStatus.BLOCKED.value, "blocked")
        )
        p_cancelled = sum(
            1
            for t in p_tasks
            if (t.status.value if hasattr(t.status, "value") else str(t.status))
            in (WorkStatus.CANCELLED.value, "cancelled")
        )
        p_sum_prog = sum(calculate_phases_progress(t.phases) for t in p_tasks)
        p_avg_prog = int(round(p_sum_prog / p_total)) if p_total > 0 else 0
        p_unfinished = p_total - p_completed

        project_summaries.append(
            ProjectProgressSummary(
                id=p.id,
                name=p.name,
                status=p.status.value if hasattr(p.status, "value") else str(p.status),
                total_tasks=p_total,
                completed_tasks=p_completed,
                in_progress_tasks=p_in_progress,
                todo_tasks=p_todo,
                blocked_tasks=p_blocked,
                cancelled_tasks=p_cancelled,
                average_progress=p_avg_prog,
                unfinished_tasks=p_unfinished,
            )
        )

    # Sort projects by most unfinished work first, then total tasks desc, then name
    project_summaries.sort(
        key=lambda x: (-x.unfinished_tasks, -x.total_tasks, x.name.lower())
    )

    return ProgressAnalyticsResponse(
        overview=overview,
        status_breakdown=status_breakdown,
        progress_distribution=progress_distribution,
        projects=project_summaries,
    )


def get_progress_insights(
    db: Session,
    user_id: int,
    project_id: Optional[int] = None,
    provider: Optional[AIProvider] = None,
) -> ProgressInsightsResponse:
    """
    Generate evidence-based AI progress insights for workspace or project.
    """
    if provider is None:
        provider = get_ai_provider()

    # Load analytics
    analytics = get_progress_analytics(db, user_id, project_id=project_id)

    # If workspace has 0 tasks, return clean empty response without calling LLM
    if analytics.overview.total_tasks == 0:
        return ProgressInsightsResponse(
            summary="Not enough task data for meaningful AI insights yet.",
            insights=[],
        )

    # Gather task context (tasks already loaded or query with options)
    task_query = (
        select(Task)
        .join(Project, Task.project_id == Project.id)
        .where(Project.user_id == user_id)
        .options(selectinload(Task.phases), selectinload(Task.project))
    )
    if project_id is not None:
        task_query = task_query.where(Task.project_id == project_id)

    tasks = list(db.execute(task_query).scalars().all())

    now_utc = datetime.now(timezone.utc)
    stalled_tasks = []
    urgent_incomplete = []
    deadline_tasks = []

    for t in tasks:
        prog = calculate_phases_progress(t.phases)
        s = t.status.value if hasattr(t.status, "value") else str(t.status)
        p = t.priority.value if hasattr(t.priority, "value") else str(t.priority)
        proj_name = t.project.name if t.project else "Unknown"

        if s in (WorkStatus.IN_PROGRESS.value, "in_progress") and prog < 25:
            stalled_tasks.append({
                "title": t.title,
                "progress": prog,
                "priority": p,
                "project_name": proj_name,
            })

        if (
            p in (TaskPriority.HIGH.value, TaskPriority.URGENT.value, "high", "urgent")
            and s not in (WorkStatus.COMPLETED.value, "completed")
        ):
            urgent_incomplete.append({
                "title": t.title,
                "progress": prog,
                "priority": p,
                "project_name": proj_name,
            })

        if t.deadline and s not in (WorkStatus.COMPLETED.value, "completed"):
            deadline_tz = t.deadline
            if deadline_tz.tzinfo is None:
                deadline_tz = deadline_tz.replace(tzinfo=timezone.utc)
            is_overdue = deadline_tz < now_utc
            deadline_tasks.append({
                "title": t.title,
                "progress": prog,
                "deadline": deadline_tz.strftime("%Y-%m-%d"),
                "is_overdue": is_overdue,
                "project_name": proj_name,
            })

    task_context = {
        "stalled_tasks": stalled_tasks,
        "urgent_incomplete": urgent_incomplete,
        "deadline_tasks": deadline_tasks,
    }

    return generate_progress_insights_ai(
        analytics_data=analytics.model_dump(),
        task_context=task_context,
        provider=provider,
    )

