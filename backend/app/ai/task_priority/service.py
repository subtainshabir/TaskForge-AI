import json
import re
from typing import Optional

from fastapi import HTTPException, status

from app.ai.base import AIProvider
from app.ai.task_priority.prompts import (
    TASK_PRIORITY_SYSTEM_PROMPT,
    build_task_priority_prompt,
)
from app.ai.task_priority.schemas import TaskPriorityAnalysisResponse
from app.models.enums import WorkStatus
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


def analyze_task_priority_ai(
    task: Task,
    provider: AIProvider,
) -> TaskPriorityAnalysisResponse:
    if not provider.is_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI service is not configured. Please configure an AI provider in backend settings.",
        )

    if task.status == WorkStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Completed tasks do not require priority analysis.",
        )

    prompt = build_task_priority_prompt(task)

    try:
        raw_response = provider.complete(
            prompt=prompt,
            system_prompt=TASK_PRIORITY_SYSTEM_PROMPT,
        )
    except HTTPException:
        raise
    except TimeoutError:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="AI service request timed out. Please try again.",
        )
    except Exception as e:
        err_msg = str(e)
        if "401" in err_msg or "unauthorized" in err_msg.lower():
            detail = "AI provider credentials rejected. Please verify backend settings."
        elif "429" in err_msg or "rate limit" in err_msg.lower():
            detail = "AI provider rate limit exceeded. Please try again shortly."
        elif "timeout" in err_msg.lower():
            detail = "AI service request timed out. Please try again."
        else:
            detail = "AI service encountered an unexpected error. Please try again."
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=detail,
        )

    try:
        data = extract_json(raw_response)
        validated = TaskPriorityAnalysisResponse.model_validate(data)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="AI provider returned an invalid structured priority output. Please try analyzing again.",
        )

    # Ensure current_priority matches actual task priority
    actual_priority = task.priority.value if hasattr(task.priority, "value") else str(task.priority)
    validated.current_priority = actual_priority

    if validated.is_inconsistent is None:
        validated.is_inconsistent = validated.recommended_priority != validated.current_priority

    return validated
