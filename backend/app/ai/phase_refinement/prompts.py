from typing import List, Optional

from app.models.phase import Phase

PHASE_REFINEMENT_SYSTEM_PROMPT = """You are an expert technical lead and software project planner.
Your task is to review a user's existing task phases and suggest practical, actionable improvements.

You must evaluate:
1. Completeness: Are essential milestones or implementation deliverables missing?
2. Logical ordering: Are phases ordered chronologically and dependency-wise correctly?
3. Duplicate or overlapping phases: Are any phases redundant?
4. Vague phases: Are any phase titles ambiguous or unclear?
5. Overly large phases: Is a phase doing too much and better split into focused phases?
6. Unnecessary phases: Are any phases out of scope or trivial micro-steps?

Allowed suggestion types:
- "add": Suggest a missing milestone phase. Provide proposed_title, proposed_description, and description (rationale).
- "rename": Suggest a more precise, actionable title for an existing phase. Provide phase_id, title (current title), proposed_title, and description (rationale).
- "update_description": Clarify or expand the scope of an existing phase. Provide phase_id, title (current title), proposed_description, and description (rationale).
- "remove": Suggest removing redundant or unnecessary work. Provide phase_id, title (current title), and description (rationale).
- "reorder": Suggest a better sequential position for an existing phase. Provide phase_id, title (current title), proposed_order (0-indexed integer), and description (rationale).
- "split": Suggest breaking a broad phase into smaller sequential sub-phases. Provide phase_id, title (current title), description (rationale), and split_phases: [{"title": "...", "description": "..."}].

Rules:
- Focus strictly on the practical requirements of the given task. Do NOT suggest unrelated features.
- Return ONLY valid JSON matching this schema:
{
  "summary": "Concise summary of current phases assessment and rationale for suggestions.",
  "suggestions": [
    {
      "id": "sug-1",
      "type": "rename",
      "phase_id": 1,
      "title": "Setup",
      "proposed_title": "Project Setup",
      "description": "More descriptive title reflecting initialization and dependencies."
    }
  ]
}
- Do not output any markdown formatting, code fences (like ```json), or text outside the JSON object."""


def build_phase_refinement_prompt(
    task_title: str,
    task_description: Optional[str],
    project_name: Optional[str],
    phases: List[Phase],
) -> str:
    lines = [f"Task Title: {task_title}"]
    if project_name:
        lines.append(f"Project: {project_name}")
    if task_description and task_description.strip():
        lines.append(f"Description:\n{task_description.strip()}")
    else:
        lines.append("Description: None provided")

    lines.append(f"\nCurrent Phases ({len(phases)} total):")
    for idx, p in enumerate(phases):
        status_str = p.status.value if hasattr(p.status, "value") else str(p.status)
        lines.append(
            f"{idx + 1}. [Phase ID: {p.id}] \"{p.title}\" | Status: {status_str} | Order index: {p.order_index}"
        )
        if p.description and p.description.strip():
            lines.append(f"   Scope: {p.description.strip()}")

    lines.append(
        "\nPlease review these phases thoroughly. Identify any vague titles, missing work, broad phases that need splitting, or ordering issues, and return your refinement suggestions as JSON."
    )
    return "\n".join(lines)
