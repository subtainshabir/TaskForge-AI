import json
import re
from fastapi import HTTPException, status

from app.ai.base import AIProvider
from app.ai.task_understanding.prompts import (
    TASK_UNDERSTANDING_SYSTEM_PROMPT,
    build_task_understanding_prompt,
)
from app.ai.task_understanding.schemas import TaskAnalysisResponse
from app.models.task import Task


def extract_json(raw_text: str) -> dict:
    cleaned = raw_text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        return json.loads(cleaned)
    except Exception:
        match = re.search(r"(\{.*\})", cleaned, re.DOTALL)
        if match:
            return json.loads(match.group(1))
        raise ValueError("Could not parse JSON from AI response")


def analyze_task_understanding(task: Task, provider: AIProvider) -> TaskAnalysisResponse:
    if not provider.is_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI service is not configured. Please configure an AI provider in backend settings.",
        )

    project_name = getattr(task, "project_name", None) or (task.project.name if getattr(task, "project", None) else None)
    deadline_str = task.deadline.isoformat() if task.deadline else None
    priority_val = task.priority.value if hasattr(task.priority, "value") else str(task.priority)

    prompt = build_task_understanding_prompt(
        title=task.title,
        description=task.description,
        priority=priority_val,
        deadline=deadline_str,
        project_name=project_name,
    )

    try:
        raw_response = provider.complete(
            prompt=prompt,
            system_prompt=TASK_UNDERSTANDING_SYSTEM_PROMPT,
        )
    except HTTPException:
        raise
    except TimeoutError:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="AI service request timed out. Please try again.",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"AI service error: {str(e)}",
        )

    try:
        data = extract_json(raw_response)
        return TaskAnalysisResponse.model_validate(data)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="AI provider returned an invalid structured output. Please try analyzing again.",
        )
