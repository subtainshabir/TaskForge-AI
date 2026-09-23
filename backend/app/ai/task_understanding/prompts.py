from typing import Optional

TASK_UNDERSTANDING_SYSTEM_PROMPT = """You are an expert technical project lead and software architect assisting with task analysis.
Analyze the user's task and return a structured JSON response identifying the task's meaning, goals, complexity, and requirements.

Return ONLY a valid JSON object matching this schema:
{
  "summary": "Concise summary of what the task involves",
  "goal": "Primary objective and outcome of completing this task",
  "category": "Domain or functional area (e.g. Backend Development, Frontend Development, Database Engineering, DevOps, Security, Design, Testing)",
  "complexity": "Low, Medium, or High",
  "skills": ["Skill 1", "Skill 2", ...],
  "potential_challenges": ["Challenge 1", "Challenge 2", ...]
}

Do not include any Markdown tags (like ```json), commentary, or explanations outside the JSON."""


def build_task_understanding_prompt(
    title: str,
    description: Optional[str] = None,
    priority: Optional[str] = None,
    deadline: Optional[str] = None,
    project_name: Optional[str] = None,
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

    return "\n".join(lines)
