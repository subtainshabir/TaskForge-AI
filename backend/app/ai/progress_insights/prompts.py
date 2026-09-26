from typing import Any, Dict

PROGRESS_INSIGHTS_SYSTEM_PROMPT = """You are TaskForge AI's Progress Analysis Engine.
Your role is to analyze current task and project progress data to provide useful, objective, evidence-based observations answering: "What does the current progress indicate?"

STRICT GUIDELINES:
1. EVIDENCE-BASED ONLY: Every insight must be directly supported by the supplied data. Never invent statistics, task counts, or assumptions.
2. NO PREDICTIONS OR COMPLETION FORECASTS: Never predict completion dates, whether the user will finish on time, or forecast future velocity.
3. NO HISTORICAL TREND CLAIMS: There is no historical data. Do not say productivity is increasing, declining, or changing over time. Use "Current data shows...", "Currently...", "At present...".
4. DEADLINE OBSERVATIONS: Only describe the objective relationship between current progress and approaching or overdue deadlines (e.g. "Task X has an approaching deadline on Y and is currently at 20% progress").
5. DO NOT MODIFY TASKS: Offer analysis and observations only.
6. INSIGHT TYPES:
   - "progress": Observations on overall progress, distribution, or task completion ratios.
   - "bottleneck": High-priority tasks or blocked tasks with low progress.
   - "stalled": Active (in-progress) tasks that have 0% or low phase progress.
   - "deadline": Incomplete tasks with urgent, approaching, or overdue deadlines.
   - "positive": Milestones, completed projects, or areas of strong completion.
7. SEVERITY: "info", "low", "medium", "high".

JSON OUTPUT FORMAT:
You must respond with valid JSON only, using this schema:
{
  "summary": "Concise 1-3 sentence high-level synthesis of current workspace progress.",
  "insights": [
    {
      "type": "bottleneck",
      "title": "Short descriptive title",
      "description": "Clear explanation grounded in the provided numbers.",
      "severity": "medium"
    }
  ]
}
"""


def build_progress_insights_prompt(
    analytics: Dict[str, Any],
    task_context: Dict[str, Any],
) -> str:
    """
    Format current analytics and contextual task data into a clean, structured prompt.
    """
    overview = analytics.get("overview", {})
    distribution = analytics.get("progress_distribution", {})
    projects = analytics.get("projects", [])

    lines = [
        "WORKSPACE CURRENT PROGRESS DATA:",
        f"- Total Tasks: {overview.get('total_tasks', 0)}",
        f"- Completed Tasks: {overview.get('completed_tasks', 0)}",
        f"- In-Progress Tasks: {overview.get('in_progress_tasks', 0)}",
        f"- Todo (Not Started) Tasks: {overview.get('todo_tasks', 0)}",
        f"- Blocked Tasks: {overview.get('blocked_tasks', 0)}",
        f"- Average Task Progress: {overview.get('average_progress', 0)}%",
        "",
        "TASK PROGRESS DISTRIBUTION:",
        f"- 0% progress: {distribution.get('p0', distribution.get('zero', 0))} tasks",
        f"- 1–24% progress: {distribution.get('p1_24', 0)} tasks",
        f"- 25–49% progress: {distribution.get('p25_49', 0)} tasks",
        f"- 50–74% progress: {distribution.get('p50_74', 0)} tasks",
        f"- 75–99% progress: {distribution.get('p75_99', 0)} tasks",
        f"- 100% progress: {distribution.get('p100', distribution.get('complete', 0))} tasks",
        "",
        "PROJECT PROGRESS BREAKDOWN:",
    ]

    if not projects:
        lines.append("- No projects recorded.")
    else:
        for p in projects:
            lines.append(
                f"- Project '{p.get('name', 'Unknown')}': {p.get('completed_tasks', 0)}/{p.get('total_tasks', 0)} tasks completed, "
                f"average progress {p.get('average_progress', 0)}%, {p.get('unfinished_tasks', 0)} unfinished tasks (Status: {p.get('status', 'active')})"
            )

    lines.append("")
    lines.append("ACTIVE & FOCUS AREAS:")

    stalled_tasks = task_context.get("stalled_tasks", [])
    if stalled_tasks:
        lines.append(f"- Active tasks with low progress (<25%): {len(stalled_tasks)}")
        for t in stalled_tasks[:5]:
            lines.append(f"  • '{t.get('title')}' in '{t.get('project_name')}' (Progress: {t.get('progress', 0)}%, Priority: {t.get('priority')})")
    else:
        lines.append("- No active tasks with <25% progress.")

    urgent_incomplete = task_context.get("urgent_incomplete", [])
    if urgent_incomplete:
        lines.append(f"- High/Urgent priority tasks not yet completed: {len(urgent_incomplete)}")
        for t in urgent_incomplete[:5]:
            lines.append(f"  • '{t.get('title')}' (Progress: {t.get('progress', 0)}%, Priority: {t.get('priority')})")

    deadline_tasks = task_context.get("deadline_tasks", [])
    if deadline_tasks:
        lines.append(f"- Incomplete tasks with deadlines: {len(deadline_tasks)}")
        for t in deadline_tasks[:5]:
            lines.append(f"  • '{t.get('title')}' (Progress: {t.get('progress', 0)}%, Due: {t.get('deadline')}, Overdue: {t.get('is_overdue', False)})")

    lines.append("")
    lines.append("Analyze this data and return the structured JSON summary and insights.")
    return "\n".join(lines)
