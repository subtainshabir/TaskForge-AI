import json
import re
from typing import Dict, List, Optional

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.ai.base import AIProvider
from app.ai.project_knowledge.prompts import (
    PROJECT_KNOWLEDGE_SYSTEM_PROMPT,
    build_project_knowledge_prompt,
    clean_note_content_for_ai,
)
from app.ai.project_knowledge.schemas import (
    ProjectAIMessage,
    ProjectAIResponse,
    ProjectAISource,
)
from app.models.enums import WorkStatus
from app.models.project import Project
from app.models.task import Task
from app.notes import service as notes_service
from app.projects.service import get_owned_project
from app.tasks.service import calculate_phases_progress

MAX_TASKS_IN_CONTEXT = 30
MAX_NOTES_IN_CONTEXT = 10


def extract_json(raw_text: str) -> dict:
    """
    Extract and parse JSON object from LLM response text, with fallback.
    """
    cleaned = raw_text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        return json.loads(cleaned)
    except Exception:
        match = re.search(r"(\{.*\})", cleaned, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except Exception:
                pass
        if cleaned:
            return {"answer": cleaned, "sources": []}
        raise ValueError("Could not parse JSON from AI response")


def build_project_context_representation(
    project: Project,
    tasks: List[Task],
    notes: list,
) -> str:
    """
    Build a compact, factual text representation of the project, its tasks, phases, and notes.
    """
    total_tasks = len(tasks)
    completed_tasks = 0
    in_progress_tasks = 0
    blocked_tasks = 0
    todo_tasks = 0
    total_progress_sum = 0

    for t in tasks:
        p_val = calculate_phases_progress(t.phases)
        total_progress_sum += p_val
        s = t.status.value if hasattr(t.status, "value") else str(t.status)
        if s in ("completed", WorkStatus.COMPLETED.value):
            completed_tasks += 1
        elif s in ("in_progress", WorkStatus.IN_PROGRESS.value):
            in_progress_tasks += 1
        elif s in ("blocked", WorkStatus.BLOCKED.value):
            blocked_tasks += 1
        elif s in ("todo", WorkStatus.TODO.value):
            todo_tasks += 1

    overall_progress = round(total_progress_sum / total_tasks) if total_tasks > 0 else 0

    lines = [
        f"PROJECT: {project.name} (ID: {project.id})",
        f"Status: {project.status.value if hasattr(project.status, 'value') else str(project.status)}",
        f"Description: {project.description or 'None provided.'}",
        f"Overall Progress: {overall_progress}% ({completed_tasks}/{total_tasks} tasks completed)",
        f"Task Breakdown: {in_progress_tasks} in progress, {blocked_tasks} blocked, {todo_tasks} to-do, {completed_tasks} completed",
        "",
        "TASKS & PHASES:",
    ]

    if not tasks:
        lines.append("- No tasks created yet.")
    else:
        # Prioritize incomplete/active tasks over completed ones
        def task_sort_key(task: Task):
            s = task.status.value if hasattr(task.status, "value") else str(task.status)
            if s in ("blocked", WorkStatus.BLOCKED.value):
                return 0
            if s in ("in_progress", WorkStatus.IN_PROGRESS.value):
                return 1
            if s in ("todo", WorkStatus.TODO.value):
                return 2
            return 3

        sorted_tasks = sorted(tasks, key=task_sort_key)
        for t in sorted_tasks[:MAX_TASKS_IN_CONTEXT]:
            s_val = t.status.value if hasattr(t.status, "value") else str(t.status)
            p_val = t.priority.value if hasattr(t.priority, "value") else str(t.priority)
            prog = calculate_phases_progress(t.phases)
            deadline_str = t.deadline.strftime("%Y-%m-%d") if t.deadline else "None"

            desc_sample = (t.description or "").strip().replace("\n", " ")[:200]
            desc_text = f" | Description: {desc_sample}" if desc_sample else ""

            lines.append(
                f"- [Task #{t.id}] \"{t.title}\" | Status: {s_val} | Priority: {p_val} | Progress: {prog}% | Deadline: {deadline_str}{desc_text}"
            )

            # Include phases for this task
            if t.phases:
                for ph in t.phases:
                    ph_status = ph.status.value if hasattr(ph.status, "value") else str(ph.status)
                    lines.append(
                        f"    Phase #{ph.id}: \"{ph.title}\" (Status: {ph_status}, Progress: {ph.progress}%)"
                    )

    lines.append("")
    lines.append("PROJECT NOTES:")
    if not notes:
        lines.append("- No project notes recorded.")
    else:
        for n in notes[:MAX_NOTES_IN_CONTEXT]:
            clean_content = clean_note_content_for_ai(n.content or "")[:800]
            clean_sample = clean_content.replace("\n", " ").strip() if clean_content else "No content"
            lines.append(f"- [Note #{n.id}] \"{n.title}\": {clean_sample}")

    return "\n".join(lines)


def answer_project_question_ai(
    db: Session,
    user_id: int,
    project_id: int,
    question: str,
    conversation_history: Optional[List[ProjectAIMessage]] = None,
    provider: Optional[AIProvider] = None,
) -> ProjectAIResponse:
    """
    Answer questions about a project using only the project's tasks, phases, notes, and progress.
    Strictly verifies ownership and does NOT modify any project data.
    """
    # 1. Question validation
    q = (question or "").strip()
    if not q:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Question cannot be empty.",
        )
    if len(q) > 1000:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Question is too long (maximum 1000 characters).",
        )

    # 2. Authorization & Ownership verification
    project = get_owned_project(db, user_id, project_id)

    # 3. Load tasks with phases and dependencies
    stmt = (
        select(Task)
        .where(Task.project_id == project_id, Task.user_id == user_id)
        .options(selectinload(Task.phases), selectinload(Task.dependencies))
    )
    tasks = list(db.execute(stmt).scalars().all())

    # 4. Load project notes
    notes = notes_service.list_project_notes(db=db, user_id=user_id, project_id=project_id)

    # 5. Check AI Provider
    if provider is None or not provider.is_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI service is not configured. Please configure an AI provider in backend settings.",
        )

    # 6. Build compact project context
    project_context = build_project_context_representation(
        project=project,
        tasks=tasks,
        notes=notes,
    )

    prompt = build_project_knowledge_prompt(
        project_context=project_context,
        question=q,
        history=conversation_history,
    )

    # 7. Complete with AI Provider
    try:
        raw_response = provider.complete(
            prompt=prompt,
            system_prompt=PROJECT_KNOWLEDGE_SYSTEM_PROMPT,
        )
    except HTTPException:
        raise
    except TimeoutError:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="AI service request timed out. Please try asking your question again.",
        )
    except Exception as e:
        err_msg = str(e).lower()
        if "401" in err_msg or "unauthorized" in err_msg:
            detail = "AI provider credentials rejected. Please verify backend settings."
        elif "429" in err_msg or "rate limit" in err_msg:
            detail = "AI provider rate limit exceeded. Please try again shortly."
        elif "timeout" in err_msg:
            detail = "AI service request timed out. Please try asking your question again."
        else:
            detail = "AI service encountered an unexpected error. Please try again."
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=detail,
        )

    # 8. Parse response
    parsed = extract_json(raw_response)
    raw_answer = str(parsed.get("answer", "")).strip()
    if not raw_answer:
        raw_answer = "The project does not contain enough information to answer that question."

    raw_sources = parsed.get("sources", [])
    if not isinstance(raw_sources, list):
        raw_sources = []

    # 9. Validate and sanitize sources against actual project data
    task_map: Dict[int, Task] = {t.id: t for t in tasks}
    note_map: Dict[int, any] = {n.id: n for n in notes}
    phase_map: Dict[int, any] = {p.id: p for t in tasks for p in t.phases}

    valid_sources: List[ProjectAISource] = []
    seen = set()

    for item in raw_sources:
        if not isinstance(item, dict):
            continue
        s_type = str(item.get("type", "")).strip().lower()
        try:
            s_id = int(item.get("id", 0))
        except (ValueError, TypeError):
            continue

        key = (s_type, s_id)
        if key in seen:
            continue

        if s_type == "task" and s_id in task_map:
            seen.add(key)
            valid_sources.append(
                ProjectAISource(type="task", id=s_id, title=task_map[s_id].title)
            )
        elif s_type == "note" and s_id in note_map:
            seen.add(key)
            valid_sources.append(
                ProjectAISource(type="note", id=s_id, title=note_map[s_id].title)
            )
        elif s_type == "phase" and s_id in phase_map:
            seen.add(key)
            valid_sources.append(
                ProjectAISource(type="phase", id=s_id, title=phase_map[s_id].title)
            )
        elif s_type == "project" and s_id == project.id:
            seen.add(key)
            valid_sources.append(
                ProjectAISource(type="project", id=project.id, title=project.name)
            )

    return ProjectAIResponse(
        answer=raw_answer,
        sources=valid_sources,
    )
