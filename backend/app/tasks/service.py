from datetime import datetime, timezone
from typing import List, Optional

from fastapi import HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload

from app.ai.base import AIProvider
from app.ai.phase_generation.service import generate_task_phases_ai
from app.ai.phase_refinement.schemas import (
    PhaseRefinementResponse,
    PhaseRefinementSuggestion,
)
from app.ai.phase_refinement.service import refine_task_phases_ai
from app.models.enums import TaskPriority, WorkStatus
from app.models.phase import Phase
from app.models.project import Project
from app.models.task import Task
from app.models.task_activity import TaskActivity
from app.models.task_dependency import TaskDependency
from app.tasks.schemas import (
    PhaseCreate,
    PhaseUpdate,
    TaskCreate,
    TaskDependencyCreate,
    TaskUpdate,
)


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


def record_activity(
    db: Session,
    task_id: int,
    user_id: int,
    activity_type: str,
    description: str,
    metadata: Optional[dict] = None,
) -> TaskActivity:
    activity = TaskActivity(
        task_id=task_id,
        user_id=user_id,
        activity_type=activity_type,
        description=description,
        activity_metadata=metadata or {},
    )
    db.add(activity)
    return activity


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
    db.flush()
    record_activity(
        db=db,
        task_id=task.id,
        user_id=user_id,
        activity_type="created",
        description="Task created",
        metadata={"title": task.title},
    )
    db.commit()
    db.refresh(task)
    return task


def update_task(
    db: Session, task: Task, payload: TaskUpdate, user_id: Optional[int] = None
) -> Task:
    actor_id = user_id or task.user_id
    provided = payload.model_fields_set

    if payload.status is not None:
        new_status = WorkStatus(payload.status)
        if new_status != task.status:
            old_val = task.status.value
            new_val = new_status.value
            task.status = new_status
            if new_status == WorkStatus.COMPLETED:
                record_activity(
                    db=db,
                    task_id=task.id,
                    user_id=actor_id,
                    activity_type="completed",
                    description="Task completed",
                    metadata={"old_status": old_val, "new_status": new_val},
                )
            else:
                old_label = old_val.replace("_", " ").capitalize()
                new_label = new_val.replace("_", " ").capitalize()
                record_activity(
                    db=db,
                    task_id=task.id,
                    user_id=actor_id,
                    activity_type="status_changed",
                    description=f"Status changed: {old_label} → {new_label}",
                    metadata={"old_status": old_val, "new_status": new_val},
                )

    if payload.priority is not None:
        new_priority = TaskPriority(payload.priority)
        if new_priority != task.priority:
            old_pri = task.priority.value
            new_pri = new_priority.value
            task.priority = new_priority
            record_activity(
                db=db,
                task_id=task.id,
                user_id=actor_id,
                activity_type="priority_changed",
                description=f"Priority changed: {old_pri.capitalize()} → {new_pri.capitalize()}",
                metadata={"old_priority": old_pri, "new_priority": new_pri},
            )

    if "deadline" in provided and payload.deadline != task.deadline:
        old_dl = task.deadline
        new_dl = payload.deadline
        task.deadline = new_dl
        if old_dl is None and new_dl is not None:
            dl_desc = "Due date added"
        elif old_dl is not None and new_dl is None:
            dl_desc = "Due date removed"
        else:
            dl_desc = "Due date changed"
        record_activity(
            db=db,
            task_id=task.id,
            user_id=actor_id,
            activity_type="deadline_changed",
            description=dl_desc,
            metadata={
                "old_deadline": old_dl.isoformat() if old_dl else None,
                "new_deadline": new_dl.isoformat() if new_dl else None,
            },
        )

    if payload.title is not None and payload.title != task.title:
        old_title = task.title
        task.title = payload.title
        record_activity(
            db=db,
            task_id=task.id,
            user_id=actor_id,
            activity_type="updated",
            description=f"Title changed to '{payload.title}'",
            metadata={"old_title": old_title, "new_title": payload.title},
        )

    if "description" in provided and payload.description != task.description:
        task.description = payload.description
        record_activity(
            db=db,
            task_id=task.id,
            user_id=actor_id,
            activity_type="updated",
            description="Description updated",
            metadata={},
        )

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
    record_activity(
        db=db,
        task_id=task_id,
        user_id=user_id,
        activity_type="dependency_added",
        description=f"Dependency added: {dep_task.title}",
        metadata={
            "dependency_task_id": dep_task.id,
            "dependency_task_title": dep_task.title,
            "dependency_task_status": dep_task.status.value,
        },
    )
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

    dep_title = (
        dependency.depends_on_task.title
        if dependency.depends_on_task
        else f"Task #{dependency.depends_on_task_id}"
    )
    dep_task_id = dependency.depends_on_task_id

    db.delete(dependency)
    record_activity(
        db=db,
        task_id=task_id,
        user_id=user_id,
        activity_type="dependency_removed",
        description=f"Dependency removed: {dep_title}",
        metadata={
            "dependency_task_id": dep_task_id,
            "dependency_task_title": dep_title,
        },
    )
    db.commit()


def list_task_activities(
    db: Session, user_id: int, task_id: int, page: int = 1, limit: int = 20
) -> List[TaskActivity]:
    get_owned_task(db, user_id, task_id)
    offset = max(0, (page - 1) * limit)
    stmt = (
        select(TaskActivity)
        .where(TaskActivity.task_id == task_id)
        .order_by(TaskActivity.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    return list(db.execute(stmt).scalars().all())


def sync_task_progress(db: Session, task: Task) -> int:
    phases = (
        db.execute(select(Phase).where(Phase.task_id == task.id))
        .scalars()
        .all()
    )
    if not phases:
        task.progress = 0
    else:
        completed = sum(1 for p in phases if p.status == WorkStatus.COMPLETED)
        task.progress = int(round((completed / len(phases)) * 100))
    return task.progress


def get_task_phases(db: Session, user_id: int, task_id: int) -> List[Phase]:
    get_owned_task(db, user_id, task_id)
    stmt = (
        select(Phase)
        .where(Phase.task_id == task_id)
        .order_by(Phase.order_index.asc(), Phase.id.asc())
    )
    return list(db.execute(stmt).scalars().all())


def create_phase(
    db: Session, user_id: int, task_id: int, payload: PhaseCreate
) -> Phase:
    task = get_owned_task(db, user_id, task_id)

    order_idx = payload.order_index if payload.order_index is not None else payload.order
    if order_idx is None:
        existing_phases = (
            db.execute(select(Phase).where(Phase.task_id == task_id))
            .scalars()
            .all()
        )
        order_idx = len(existing_phases)

    status_val = WorkStatus(payload.status or "todo")
    is_completed = status_val == WorkStatus.COMPLETED
    completed_time = datetime.now(timezone.utc) if is_completed else None

    phase = Phase(
        task_id=task.id,
        title=payload.title,
        description=payload.description,
        order_index=order_idx,
        status=status_val,
        progress=100 if is_completed else 0,
        completed_at=completed_time,
    )
    db.add(phase)
    db.flush()

    record_activity(
        db=db,
        task_id=task.id,
        user_id=user_id,
        activity_type="phase_created",
        description=f'Phase added: "{phase.title}"',
        metadata={"phase_id": phase.id, "phase_title": phase.title},
    )

    sync_task_progress(db, task)
    db.commit()
    db.refresh(phase)
    return phase


def update_phase(
    db: Session, user_id: int, task_id: int, phase_id: int, payload: PhaseUpdate
) -> Phase:
    task = get_owned_task(db, user_id, task_id)
    phase = db.execute(
        select(Phase).where(Phase.id == phase_id, Phase.task_id == task_id)
    ).scalar_one_or_none()

    if phase is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Phase not found"
        )

    if payload.title is not None and payload.title != phase.title:
        phase.title = payload.title

    if "description" in payload.model_fields_set:
        phase.description = payload.description

    order_idx = payload.order_index if payload.order_index is not None else payload.order
    if order_idx is not None:
        phase.order_index = order_idx

    if payload.status is not None:
        new_status = WorkStatus(payload.status)
        if new_status != phase.status:
            old_status = phase.status
            phase.status = new_status
            if new_status == WorkStatus.COMPLETED:
                phase.progress = 100
                phase.completed_at = datetime.now(timezone.utc)
                record_activity(
                    db=db,
                    task_id=task.id,
                    user_id=user_id,
                    activity_type="phase_completed",
                    description=f'Phase completed: "{phase.title}"',
                    metadata={"phase_id": phase.id, "phase_title": phase.title},
                )
            else:
                phase.completed_at = None
                if old_status == WorkStatus.COMPLETED:
                    phase.progress = 0
                record_activity(
                    db=db,
                    task_id=task.id,
                    user_id=user_id,
                    activity_type="phase_updated",
                    description=f'Phase status changed: "{phase.title}" ({new_status.value})',
                    metadata={
                        "phase_id": phase.id,
                        "phase_title": phase.title,
                        "new_status": new_status.value,
                    },
                )

    if payload.progress is not None and phase.status != WorkStatus.COMPLETED:
        phase.progress = max(0, min(100, payload.progress))

    sync_task_progress(db, task)
    db.commit()
    db.refresh(phase)
    return phase


def delete_phase(db: Session, user_id: int, task_id: int, phase_id: int) -> None:
    task = get_owned_task(db, user_id, task_id)
    phase = db.execute(
        select(Phase).where(Phase.id == phase_id, Phase.task_id == task_id)
    ).scalar_one_or_none()

    if phase is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Phase not found"
        )

    title = phase.title
    db.delete(phase)
    db.flush()

    record_activity(
        db=db,
        task_id=task.id,
        user_id=user_id,
        activity_type="phase_deleted",
        description=f'Phase deleted: "{title}"',
        metadata={"phase_id": phase_id, "phase_title": title},
    )

    sync_task_progress(db, task)
    db.commit()


def generate_task_phases(
    db: Session,
    user_id: int,
    task_id: int,
    provider: AIProvider,
    replace_existing: bool = False,
) -> List[Phase]:
    task = get_owned_task(db, user_id, task_id)
    existing = (
        db.execute(
            select(Phase)
            .where(Phase.task_id == task_id)
            .order_by(Phase.order_index.asc())
        )
        .scalars()
        .all()
    )

    if existing and not replace_existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Task already has phases. Confirm regeneration to replace existing phases.",
        )

    if existing and replace_existing:
        for p in existing:
            db.delete(p)
        db.flush()

    generated_items = generate_task_phases_ai(task=task, provider=provider)

    created_phases = []
    for idx, item in enumerate(generated_items):
        phase = Phase(
            task_id=task.id,
            title=item.title,
            description=item.description,
            order_index=idx,
            status=WorkStatus.TODO,
            progress=0,
        )
        db.add(phase)
        created_phases.append(phase)
    db.flush()

    act_desc = (
        f"Regenerated {len(created_phases)} phases with AI"
        if (existing and replace_existing)
        else f"Generated {len(created_phases)} phases with AI"
    )
    record_activity(
        db=db,
        task_id=task.id,
        user_id=user_id,
        activity_type="phases_generated",
        description=act_desc,
        metadata={"count": len(created_phases), "replaced": bool(existing and replace_existing)},
    )

    sync_task_progress(db, task)
    db.commit()

    return (
        db.execute(
            select(Phase)
            .where(Phase.task_id == task_id)
            .order_by(Phase.order_index.asc(), Phase.id.asc())
        )
        .scalars()
        .all()
    )


def refine_task_phases(
    db: Session,
    user_id: int,
    task_id: int,
    provider: AIProvider,
) -> PhaseRefinementResponse:
    task = get_owned_task(db, user_id, task_id)
    phases = get_task_phases(db, user_id, task_id)
    if not phases:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Task has no phases to refine. Please add or generate phases first.",
        )
    return refine_task_phases_ai(task=task, phases=phases, provider=provider)


def apply_phase_refinements(
    db: Session,
    user_id: int,
    task_id: int,
    suggestions: List[PhaseRefinementSuggestion],
) -> List[Phase]:
    task = get_owned_task(db, user_id, task_id)
    if not suggestions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No suggestions provided to apply.",
        )

    existing_phases = get_task_phases(db, user_id, task_id)
    phase_map = {p.id: p for p in existing_phases}

    allowed_types = {"add", "rename", "update_description", "remove", "reorder", "split"}
    targeted_phase_operations = {}

    for sug in suggestions:
        if sug.type not in allowed_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported suggestion type '{sug.type}'.",
            )

        if sug.type in ("rename", "update_description", "remove", "reorder", "split"):
            if sug.phase_id is None or sug.phase_id not in phase_map:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Phase #{sug.phase_id} does not belong to this task or does not exist.",
                )
            prev_op = targeted_phase_operations.get(sug.phase_id)
            if prev_op and (prev_op in ("remove", "split") or sug.type in ("remove", "split")):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Conflicting suggestions detected for phase #{sug.phase_id}.",
                )
            targeted_phase_operations[sug.phase_id] = sug.type

        if sug.type == "add":
            title = (sug.proposed_title or sug.title or "").strip()
            if not title:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Title is required for adding a phase.",
                )
            if len(title) > 255:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Phase title cannot exceed 255 characters.",
                )

        elif sug.type == "rename":
            title = (sug.proposed_title or sug.title or "").strip()
            if not title:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Proposed title is required for renaming a phase.",
                )
            if len(title) > 255:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Phase title cannot exceed 255 characters.",
                )

        elif sug.type == "split":
            if not sug.split_phases:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Split suggestion must specify at least one replacement phase.",
                )
            for item in sug.split_phases:
                t = (item.title or "").strip()
                if not t:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="All split phases must have a non-empty title.",
                    )
                if len(t) > 255:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Phase title cannot exceed 255 characters.",
                    )

    deleted_ids = set()
    applied_count = 0

    for sug in suggestions:
        if sug.type == "remove":
            phase = phase_map.get(sug.phase_id)
            if phase and phase.id not in deleted_ids:
                old_title = phase.title
                db.delete(phase)
                deleted_ids.add(phase.id)
                applied_count += 1
                record_activity(
                    db=db,
                    task_id=task.id,
                    user_id=user_id,
                    activity_type="phase_deleted",
                    description=f'Phase removed: "{old_title}"',
                    metadata={"phase_id": sug.phase_id, "phase_title": old_title},
                )

        elif sug.type == "rename":
            phase = phase_map.get(sug.phase_id)
            if phase and phase.id not in deleted_ids:
                old_title = phase.title
                new_title = (sug.proposed_title or sug.title or "").strip()
                phase.title = new_title
                applied_count += 1
                record_activity(
                    db=db,
                    task_id=task.id,
                    user_id=user_id,
                    activity_type="phase_renamed",
                    description=f'Phase renamed: "{old_title}" → "{new_title}"',
                    metadata={"phase_id": phase.id, "old_title": old_title, "new_title": new_title},
                )

        elif sug.type == "update_description":
            phase = phase_map.get(sug.phase_id)
            if phase and phase.id not in deleted_ids:
                new_desc = (sug.proposed_description or sug.description or "").strip() or None
                phase.description = new_desc
                applied_count += 1
                record_activity(
                    db=db,
                    task_id=task.id,
                    user_id=user_id,
                    activity_type="phase_updated",
                    description=f'Phase description updated: "{phase.title}"',
                    metadata={"phase_id": phase.id, "phase_title": phase.title},
                )

        elif sug.type == "reorder":
            phase = phase_map.get(sug.phase_id)
            if phase and phase.id not in deleted_ids:
                target_order = max(0, sug.proposed_order if sug.proposed_order is not None else 0)
                phase.order_index = target_order
                applied_count += 1
                record_activity(
                    db=db,
                    task_id=task.id,
                    user_id=user_id,
                    activity_type="phase_reordered",
                    description=f'Phase reordered: "{phase.title}"',
                    metadata={"phase_id": phase.id, "phase_title": phase.title, "new_order": target_order},
                )

        elif sug.type == "split":
            phase = phase_map.get(sug.phase_id)
            if phase and phase.id not in deleted_ids:
                orig_title = phase.title
                orig_order = phase.order_index
                db.delete(phase)
                deleted_ids.add(phase.id)

                for idx, sp in enumerate(sug.split_phases):
                    new_phase = Phase(
                        task_id=task.id,
                        title=sp.title.strip(),
                        description=sp.description.strip() if sp.description and sp.description.strip() else None,
                        order_index=orig_order + idx,
                        status=WorkStatus.TODO,
                        progress=0,
                    )
                    db.add(new_phase)
                    record_activity(
                        db=db,
                        task_id=task.id,
                        user_id=user_id,
                        activity_type="phase_created",
                        description=f'Phase added: "{new_phase.title}"',
                        metadata={"phase_title": new_phase.title, "split_from": orig_title},
                    )

                applied_count += 1
                record_activity(
                    db=db,
                    task_id=task.id,
                    user_id=user_id,
                    activity_type="phase_split",
                    description=f'Phase split: "{orig_title}" into {len(sug.split_phases)} phases',
                    metadata={"phase_id": sug.phase_id, "orig_title": orig_title, "count": len(sug.split_phases)},
                )

        elif sug.type == "add":
            title = (sug.proposed_title or sug.title or "").strip()
            desc = (sug.proposed_description or sug.description or "").strip() or None
            order_idx = sug.proposed_order if sug.proposed_order is not None else 9999
            new_phase = Phase(
                task_id=task.id,
                title=title,
                description=desc,
                order_index=order_idx,
                status=WorkStatus.TODO,
                progress=0,
            )
            db.add(new_phase)
            applied_count += 1
            record_activity(
                db=db,
                task_id=task.id,
                user_id=user_id,
                activity_type="phase_created",
                description=f'Phase added: "{title}"',
                metadata={"phase_title": title},
            )

    db.flush()
    remaining_phases = list(
        db.execute(
            select(Phase).where(Phase.task_id == task.id)
        ).scalars().all()
    )
    remaining_phases.sort(key=lambda p: (p.order_index, p.id))
    for idx, p in enumerate(remaining_phases):
        p.order_index = idx

    record_activity(
        db=db,
        task_id=task.id,
        user_id=user_id,
        activity_type="ai_phase_refinement_applied",
        description="AI phase refinement applied",
        metadata={
            "applied_count": applied_count,
            "suggestions_count": len(suggestions),
        },
    )

    sync_task_progress(db, task)
    db.commit()

    return list(
        db.execute(
            select(Phase)
            .where(Phase.task_id == task.id)
            .order_by(Phase.order_index.asc(), Phase.id.asc())
        ).scalars().all()
    )