from typing import Optional

from app.ai.task_understanding.schemas import TaskAnalysisResponse

PHASE_GENERATION_SYSTEM_PROMPT = """You are an expert technical lead and software project planner.
Break down the provided task into practical, actionable, and logical implementation phases.

Guidelines:
- Generate between 3 and 12 sequential, independently completable implementation phases based on task complexity:
  * Simple task: 3–5 phases
  * Medium task: 5–8 phases
  * Complex task: 8–12 phases
- Each phase must represent a concrete, meaningful milestone or deliverable.
- Each phase must have a clear, actionable title (under 80 characters) and a brief description explaining what work is involved.
- Phases must be arranged in chronological execution order.
- Do NOT generate vague advice, duplicate phases, or trivial micro-steps.
- Do NOT repeat the entire task description as a phase.

Return ONLY a valid JSON object matching this schema:
{
  "phases": [
    {
      "title": "Phase Title",
      "description": "Concise description of the work in this phase."
    }
  ]
}

Do not include any Markdown tags (like ```json), commentary, or explanations outside the JSON."""


def build_phase_generation_prompt(
    title: str,
    description: Optional[str] = None,
    priority: Optional[str] = None,
    deadline: Optional[str] = None,
    project_name: Optional[str] = None,
    task_understanding: Optional[TaskAnalysisResponse] = None,
) -> str:
    lines = [f"Task Title: {title}"]
    if project_name:
        lines.append(f"Project: {project_name}")
    if priority:
        lines.append(f"Priority: {priority}")
    if deadline:
        lines.append(f"Deadline: {deadline}")
    if description and description.strip():
        lines.append(f"Description:\n{description.strip()}")
    else:
        lines.append("Description: None provided")

    if task_understanding:
        lines.append("\nAI Task Context:")
        if task_understanding.summary:
            lines.append(f"- Summary: {task_understanding.summary}")
        if task_understanding.goal:
            lines.append(f"- Goal: {task_understanding.goal}")
        if task_understanding.category:
            lines.append(f"- Category: {task_understanding.category}")
        if task_understanding.complexity:
            lines.append(f"- Complexity: {task_understanding.complexity}")
        if task_understanding.skills:
            lines.append(f"- Required Skills: {', '.join(task_understanding.skills)}")
        if task_understanding.potential_challenges:
            lines.append(
                f"- Potential Challenges: {', '.join(task_understanding.potential_challenges)}"
            )

    return "\n".join(lines)
