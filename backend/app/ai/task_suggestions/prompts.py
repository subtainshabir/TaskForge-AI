from typing import List, Optional

from app.models.project import Project
from app.models.task import Task

TASK_SUGGESTIONS_SYSTEM_PROMPT = """You are an expert technical lead, software architect, and project planner.
Your objective is to analyze the project or task context and identify missing, high-value, or complementary tasks that should be considered.

Potential Suggestion Categories:
- Missing implementation tasks
- Testing and quality assurance tasks (unit, integration, regression)
- Documentation tasks (API documentation, developer setup, operational runbooks)
- Integration tasks (third-party services, payment gateways, webhooks, auth)
- Validation and error-handling tasks (input sanitization, fallback states, failure recovery)
- Deployment and infrastructure tasks (CI/CD, containerization, environment setup)
- Security tasks (authentication hardening, authorization bounds, secret handling)

Guidelines:
- Only suggest tasks that are genuinely relevant and beneficial to the given project context.
- Do NOT suggest tasks that already exist in the project or task list.
- Do NOT suggest vague or redundant tasks.
- Each suggestion must have:
  * "title": A clear, concise, actionable title (e.g. "Add Payment Failure Handling").
  * "description": A short explanation of the concrete work to be done.
  * "reason": A specific justification explaining why this task is needed based on current project progress.
  * "priority": "low", "medium", "high", or "urgent" (default to "medium" unless clearly justified).
  * "phase_title": Optional name of an appropriate milestone/phase, if applicable.
- If the current tasks already cover the necessary project scope well, return an empty suggestions list: {"suggestions": []}.
- Do NOT invent fake or trivial tasks.

Return ONLY a valid JSON object matching this schema:
{
  "suggestions": [
    {
      "title": "Add API Integration Tests",
      "description": "Test the critical authentication and product APIs.",
      "reason": "The project currently has implementation tasks but no testing coverage task.",
      "priority": "medium"
    }
  ]
}

Do not include any Markdown code blocks (like ```json), commentary, or extra text outside the JSON object."""


def build_project_task_suggestions_prompt(project: Project, tasks: List[Task]) -> str:
    lines = [f"Project: {project.name}"]
    if project.description and project.description.strip():
        lines.append(f"Description: {project.description.strip()}")
    else:
        lines.append("Description: None provided")

    lines.append(f"Project Status: {project.status.value if hasattr(project.status, 'value') else str(project.status)}")
    lines.append(f"\nExisting Tasks ({len(tasks)}):")

    if tasks:
        for t in tasks[:50]:
            pri = t.priority.value if hasattr(t.priority, "value") else str(t.priority)
            st = t.status.value if hasattr(t.status, "value") else str(t.status)
            dl_str = ""
            if t.deadline:
                dl_str = f", Deadline: {t.deadline.strftime('%Y-%m-%d')}"
            phases_count = len(getattr(t, "phases", []) or [])
            phase_info = f", Phases: {phases_count}" if phases_count > 0 else ""
            deps_count = len(getattr(t, "dependencies", []) or [])
            dep_info = f", Deps: {deps_count}" if deps_count > 0 else ""
            lines.append(f"- {t.title} (Status: {st}, Priority: {pri}{dl_str}{phase_info}{dep_info})")
            if t.description and t.description.strip():
                short_desc = t.description.strip()[:140].replace("\n", " ")
                lines.append(f"  Details: {short_desc}")
    else:
        lines.append("- (No tasks created yet)")

    lines.append(
        "\nAnalyze the above project and existing tasks. Identify 3 to 6 missing, complementary, or critical next tasks that would help complete or mature this project. If the scope is already complete, return an empty suggestions array."
    )
    return "\n".join(lines)


def build_task_level_suggestions_prompt(task: Task, project_tasks: List[Task]) -> str:
    lines = [f"Task Title: {task.title}"]
    project_name = getattr(task, "project_name", None) or (
        task.project.name if getattr(task, "project", None) else None
    )
    if project_name:
        lines.append(f"Project: {project_name}")

    pri = task.priority.value if hasattr(task.priority, "value") else str(task.priority)
    st = task.status.value if hasattr(task.status, "value") else str(task.status)
    lines.append(f"Priority: {pri}")
    lines.append(f"Status: {st}")

    if task.deadline:
        dl_str = task.deadline.strftime("%Y-%m-%d %H:%M UTC") if hasattr(task.deadline, "strftime") else str(task.deadline)
        lines.append(f"Deadline: {dl_str}")

    if task.description and task.description.strip():
        lines.append(f"Description:\n{task.description.strip()}")
    else:
        lines.append("Description: None provided")

    # Phases and subtasks
    phases = getattr(task, "phases", []) or []
    if phases:
        phase_titles = [f"'{p.title}'" for p in phases[:6]]
        lines.append(f"Phases: {', '.join(phase_titles)}")
        subtask_count = sum(len(getattr(p, "subtasks", []) or []) for p in phases)
        if subtask_count > 0:
            lines.append(f"Total Subtasks: {subtask_count}")

    # Dependencies
    dependencies = getattr(task, "dependencies", []) or []
    if dependencies:
        lines.append(f"Dependencies: Task depends on {len(dependencies)} other task(s)")

    # Other tasks in the project to avoid suggesting them
    other_tasks = [t for t in project_tasks if t.id != task.id]
    if other_tasks:
        lines.append(f"\nOther Existing Tasks in Project ({len(other_tasks)}):")
        for ot in other_tasks[:30]:
            ot_st = ot.status.value if hasattr(ot.status, "value") else str(ot.status)
            lines.append(f"- {ot.title} (Status: {ot_st})")

    lines.append(
        "\nAnalyze this task and its project context. Suggest 2 to 4 complementary, follow-up, or related tasks (such as testing, error handling, validation, monitoring, or downstream workflows) that are not already covered. If no additional tasks are needed, return an empty suggestions array."
    )
    return "\n".join(lines)
