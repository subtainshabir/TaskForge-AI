from datetime import datetime, timezone
from typing import List, Optional

from app.models.task import Task

TASK_PRIORITY_SYSTEM_PROMPT = """You are an expert technical lead and software project manager.
Your task is to analyze a task's full context and evaluate whether its current priority appears appropriate.

Available priority levels:
- "low": Minor improvements, nice-to-have items, tasks with no hard deadline or external blockers.
- "medium": Standard features, normal progression work with reasonable timelines.
- "high": Critical path deliverables, imminent deadlines, blocking dependencies, or customer-impacting issues.
- "urgent": Critical outages, active blocking bottlenecks, severe payment/security failures, or immediate hard deadlines.

Evaluation Guidelines:
1. Deadlines:
   - If no deadline is specified, do NOT assume a deadline. Evaluate priority based on scope, impact, and dependencies.
   - If a deadline is approaching or overdue, factor that into urgency.
2. Dependencies:
   - If other tasks depend on this task (this task blocks others), its priority is naturally higher.
   - If this task itself is blocked by upstream dependencies, distinguish between importance, urgency, and blocked status. Do NOT automatically mark a task as urgent just because it is blocked.
3. Impact:
   - Core checkout, payment, security, or authentication failures carry higher priority than cosmetic or routine tasks.
4. Confidence:
   - Provide a realistic confidence value between 0.0 and 1.0 (e.g. 0.85).

Return ONLY valid JSON matching this schema:
{
  "current_priority": "medium",
  "recommended_priority": "high",
  "confidence": 0.88,
  "reasoning": "Clear explanation of why this priority is recommended.",
  "factors": [
    "Key factor 1",
    "Key factor 2"
  ],
  "is_inconsistent": true
}

Do not include any code fences (like ```json), markdown formatting, or text outside the JSON object."""


def build_task_priority_prompt(task: Task) -> str:
    lines = [f"Task Title: {task.title}"]

    project_name = getattr(task, "project_name", None) or (
        task.project.name if getattr(task, "project", None) else None
    )
    if project_name:
        lines.append(f"Project: {project_name}")

    curr_priority = task.priority.value if hasattr(task.priority, "value") else str(task.priority)
    curr_status = task.status.value if hasattr(task.status, "value") else str(task.status)
    lines.append(f"Current Priority: {curr_priority}")
    lines.append(f"Current Status: {curr_status}")

    # Deadline & Overdue check
    if task.deadline:
        dl_str = task.deadline.strftime("%Y-%m-%d %H:%M UTC") if hasattr(task.deadline, "strftime") else str(task.deadline)
        now_utc = datetime.now(timezone.utc)
        # Handle timezone-naive vs timezone-aware
        task_dl = task.deadline
        if task_dl.tzinfo is None:
            task_dl = task_dl.replace(tzinfo=timezone.utc)
        is_overdue = task_dl < now_utc
        lines.append(f"Deadline: {dl_str} ({'OVERDUE' if is_overdue else 'Approaching'})")
    else:
        lines.append("Deadline: None set")

    if task.description and task.description.strip():
        lines.append(f"Description:\n{task.description.strip()}")
    else:
        lines.append("Description: None provided")

    # Dependencies context
    dependencies = getattr(task, "dependencies", []) or []
    if dependencies:
        dep_titles = []
        for d in dependencies:
            dep_task = getattr(d, "depends_on_task", None)
            if dep_task:
                dep_status = dep_task.status.value if hasattr(dep_task.status, "value") else str(dep_task.status)
                dep_titles.append(f"'{dep_task.title}' ({dep_status})")
        dep_str = f": {', '.join(dep_titles)}" if dep_titles else ""
        lines.append(f"Upstream Dependencies: Task depends on {len(dependencies)} other task(s){dep_str}")
        if task.is_blocked:
            lines.append("Blocked Status: This task is currently BLOCKED by incomplete upstream dependencies. (Note: Do not confuse blocked status with urgency).")
    else:
        lines.append("Upstream Dependencies: None (not blocked)")

    # Downstream dependents (tasks that depend on this task)
    dependents = getattr(task, "dependents", []) or []
    if dependents:
        dependent_titles = []
        for d in dependents:
            blocked_task = getattr(d, "task", None)
            if blocked_task:
                dependent_titles.append(f"'{blocked_task.title}'")
        dep_str = f": {', '.join(dependent_titles)}" if dependent_titles else ""
        lines.append(f"Downstream Impact: This task BLOCKS {len(dependents)} other dependent task(s){dep_str}.")

    # Phases context
    phases = getattr(task, "phases", []) or []
    if phases:
        completed_phases = sum(1 for p in phases if getattr(p, "status", None) and (p.status.value if hasattr(p.status, "value") else str(p.status)) == "completed")
        lines.append(f"Phases: {completed_phases} of {len(phases)} implementation phases completed ({task.progress}% progress)")

    lines.append(
        "\nPlease analyze the above task context and determine if the current priority is appropriate. Return your recommendation as JSON."
    )
    return "\n".join(lines)
