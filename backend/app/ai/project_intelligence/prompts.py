from typing import Any, Dict, List

PROJECT_INTELLIGENCE_SYSTEM_PROMPT = """You are TaskForge AI's Project Progress Intelligence Engine.
Your role is to analyze a specific project's current state and provide useful, objective, evidence-based observations answering: "What does the current progress indicate about this project?"

STRICT GUIDELINES:
1. EVIDENCE-BASED ONLY: Every insight must be directly supported by the supplied project data. Never invent statistics, task counts, progress percentages, deadlines, priorities, project risks, or assumptions.
2. NO FUTURE PREDICTIONS: Never predict project completion dates, probability of completion, future velocity, future productivity, or whether the project will succeed or fail.
3. CURRENT OBSERVATIONS ONLY: Identify current concerns and state based on existing deadlines, task statuses, progress, and workload.
   For example: "3 tasks have deadlines within the next 7 days and remain below 50% progress." That is a current observation, not a prediction.
4. DO NOT MODIFY TASKS OR PROJECTS: You are an analytical observer only. Do not suggest or make automatic task or priority changes.
5. IF DATA IS LIMITED: State clearly that the project has limited task data, so only basic progress observations can be made.
6. INSIGHT TYPES:
   - "progress": Observations on overall project progress, completed vs incomplete work, or phase completion rates.
   - "bottleneck": Stalled tasks, blocked tasks, or active tasks with low progress.
   - "priority": High-priority or urgent tasks that remain incomplete or below 50% progress.
   - "deadline": Incomplete tasks with overdue deadlines or approaching deadlines.
   - "workload": Distribution of unfinished work across statuses or functional areas.
   - "positive": Completed milestones, high progress achievements, or well-progressed work.
7. SEVERITY LEVELS:
   - "info", "low", "medium", "high".

JSON OUTPUT FORMAT:
Respond with valid JSON only, using this schema:
{
  "project_summary": "Concise 1-3 sentence synthesis of the current project state and progress.",
  "overall_progress": 64,
  "insights": [
    {
      "type": "priority",
      "title": "High-priority work remains incomplete",
      "description": "Three high-priority tasks are below 50% progress.",
      "severity": "medium"
    }
  ]
}
"""


def build_project_intelligence_prompt(
    project_info: Dict[str, Any],
    stats: Dict[str, Any],
    task_breakdown: Dict[str, Any],
) -> str:
    """
    Format current project statistics and contextual task data into a clean, structured prompt.
    """
    total_tasks = stats.get("total_tasks", 0)
    completed_tasks = stats.get("completed_tasks", 0)
    in_progress_tasks = stats.get("in_progress_tasks", 0)
    todo_tasks = stats.get("todo_tasks", 0)
    blocked_tasks = stats.get("blocked_tasks", 0)
    cancelled_tasks = stats.get("cancelled_tasks", 0)
    avg_progress = stats.get("average_task_progress", stats.get("average_progress", 0))

    lines = [
        f"PROJECT: {project_info.get('name', 'Untitled')}",
        f"Description: {project_info.get('description') or 'No description provided.'}",
        f"Status: {project_info.get('status', 'active')}",
        "",
        "PROJECT PROGRESS STATISTICS:",
        f"- Total Tasks: {total_tasks}",
        f"- Completed Tasks: {completed_tasks}",
        f"- In-Progress Tasks: {in_progress_tasks}",
        f"- Todo (Not Started) Tasks: {todo_tasks}",
        f"- Blocked Tasks: {blocked_tasks}",
        f"- Cancelled Tasks: {cancelled_tasks}",
        f"- Average Task Progress: {avg_progress}%",
        f"- Incomplete Tasks: {total_tasks - completed_tasks}",
        "",
    ]

    high_priority_incomplete = task_breakdown.get("high_priority_incomplete", [])
    if high_priority_incomplete:
        lines.append(f"HIGH-PRIORITY INCOMPLETE WORK ({len(high_priority_incomplete)} tasks):")
        for t in high_priority_incomplete[:8]:
            lines.append(
                f"- '{t.get('title')}' (Priority: {t.get('priority')}, Progress: {t.get('progress', 0)}%, Status: {t.get('status')})"
            )
        lines.append("")
    else:
        lines.append("HIGH-PRIORITY INCOMPLETE WORK: None (all high-priority tasks are completed or none exist).\n")

    stalled_tasks = task_breakdown.get("stalled_tasks", [])
    if stalled_tasks:
        lines.append(f"STALLED / LOW PROGRESS ACTIVE TASKS ({len(stalled_tasks)} in-progress tasks < 25%):")
        for t in stalled_tasks[:8]:
            lines.append(
                f"- '{t.get('title')}' (Progress: {t.get('progress', 0)}%, Priority: {t.get('priority')})"
            )
        lines.append("")
    else:
        lines.append("STALLED / LOW PROGRESS ACTIVE TASKS: None identified.\n")

    overdue_tasks = task_breakdown.get("overdue_tasks", [])
    upcoming_deadlines = task_breakdown.get("upcoming_deadline_tasks", [])
    if overdue_tasks or upcoming_deadlines:
        lines.append("DEADLINE OBSERVATIONS:")
        if overdue_tasks:
            lines.append(f"- Overdue Incomplete Tasks ({len(overdue_tasks)}):")
            for t in overdue_tasks[:5]:
                lines.append(
                    f"  • '{t.get('title')}' (Due: {t.get('deadline')}, Progress: {t.get('progress', 0)}%, Priority: {t.get('priority')})"
                )
        if upcoming_deadlines:
            lines.append(f"- Approaching Deadlines Within 7 Days ({len(upcoming_deadlines)}):")
            for t in upcoming_deadlines[:5]:
                lines.append(
                    f"  • '{t.get('title')}' (Due: {t.get('deadline')}, Progress: {t.get('progress', 0)}%, Priority: {t.get('priority')})"
                )
        lines.append("")
    else:
        lines.append("DEADLINE OBSERVATIONS: No overdue or approaching deadlines within 7 days.\n")

    workload_summary = task_breakdown.get("workload_summary", [])
    if workload_summary:
        lines.append("WORKLOAD DISTRIBUTION & CONCENTRATION:")
        for item in workload_summary:
            lines.append(f"- {item}")
        lines.append("")

    all_tasks = task_breakdown.get("tasks_summary", [])
    if all_tasks:
        lines.append(f"ALL PROJECT TASKS ({len(all_tasks)} total):")
        for t in all_tasks[:20]:
            dep_info = f", Dependencies: {t.get('dependencies_count', 0)}" if t.get('dependencies_count') else ""
            phase_info = f", Phases: {t.get('phases_count', 0)}" if t.get('phases_count') is not None else ""
            lines.append(
                f"- '{t.get('title')}' [{t.get('status')}, {t.get('priority')}] - Progress: {t.get('progress', 0)}%{phase_info}{dep_info}"
            )
        if len(all_tasks) > 20:
            lines.append(f"- ... and {len(all_tasks) - 20} more tasks.")
        lines.append("")

    lines.append(
        "Analyze this specific project data and return the structured JSON summary, overall_progress, and insights array."
    )
    return "\n".join(lines)
