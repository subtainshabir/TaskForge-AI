from typing import Optional

from app.models.task import Task

TASK_REGENERATION_SYSTEM_PROMPT = """You are an expert technical lead, engineering manager, and software architect.
Your objective is to improve an existing task definition by making it significantly clearer, more specific, more actionable, and complete, while strictly preserving its original intent and core objective.

Regeneration Principles:
1. Preserve Original Intent: Do NOT arbitrarily alter the core goal or domain of the task (e.g., do not turn an auth bug into a database migration unless directly related).
2. Improve Title:
   * Replace vague or terse titles (e.g. "Fix login", "Update API") with clear, descriptive titles indicating the component, action, and expected behavior.
   * Keep titles under 120 characters and easily scannable.
3. Improve Description:
   * Provide a concise background/problem statement explaining what is being solved.
   * Clearly define the scope of work and implementation steps.
   * Include concrete acceptance criteria or a measurable "Definition of Done".
4. Follow User Instructions:
   * If a custom user instruction is provided (e.g. "Make this task suitable for a backend developer" or "Add acceptance criteria"), follow it attentively while preserving the task purpose.
   * If no custom instruction is given, apply general best-practice task refinement.
5. Highlight Specific Improvements:
   * Include 2 to 5 bullet points in "changes" that explain exactly what was improved (e.g., "Clarified specific error conditions", "Added acceptance criteria").

Return ONLY a valid JSON object matching this schema:
{
  "title": "Fix authentication failure during user login",
  "description": "Investigate and resolve the authentication failure occurring when valid credentials are submitted. Verify token generation, error response status codes, and confirm seamless redirection upon successful login.",
  "changes": [
    "Clarified the problem statement and error scenario",
    "Defined expected outcome and definition of done",
    "Made implementation steps actionable"
  ]
}

Do not include any Markdown code blocks (like ```json), commentary, or extra text outside the JSON object."""


def build_task_regeneration_prompt(
    task: Task, instruction: Optional[str] = None
) -> str:
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
        dl_str = (
            task.deadline.strftime("%Y-%m-%d %H:%M UTC")
            if hasattr(task.deadline, "strftime")
            else str(task.deadline)
        )
        lines.append(f"Deadline: {dl_str}")

    if task.description and task.description.strip():
        lines.append(f"Current Description:\n{task.description.strip()}")
    else:
        lines.append("Current Description: (None provided - task lacks a description)")

    # Phases and subtasks context
    phases = getattr(task, "phases", []) or []
    if phases:
        phase_titles = [f"'{p.title}'" for p in phases[:6]]
        lines.append(f"Associated Phases ({len(phases)}): {', '.join(phase_titles)}")
        subtask_count = sum(len(getattr(p, "subtasks", []) or []) for p in phases)
        if subtask_count > 0:
            lines.append(f"Total Subtasks: {subtask_count}")

    # Dependencies context
    dependencies = getattr(task, "dependencies", []) or []
    if dependencies:
        lines.append(f"Dependencies: Task depends on {len(dependencies)} other task(s)")

    if instruction and instruction.strip():
        lines.append(f"\nUser Instruction:\n{instruction.strip()}")
        lines.append(
            "\nPlease rewrite and improve the task title and description following the user's specific instruction, while preserving the task's fundamental purpose."
        )
    else:
        lines.append(
            "\nPlease rewrite and improve this task to be more specific, actionable, and complete with clear acceptance criteria, preserving its original purpose."
        )

    return "\n".join(lines)
