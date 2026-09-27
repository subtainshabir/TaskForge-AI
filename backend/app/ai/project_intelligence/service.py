import json
import re
from typing import Any, Dict

from fastapi import HTTPException, status

from app.ai.base import AIProvider
from app.ai.project_intelligence.prompts import (
    PROJECT_INTELLIGENCE_SYSTEM_PROMPT,
    build_project_intelligence_prompt,
)
from app.ai.project_intelligence.schemas import (
    ProjectProgressInsight,
    ProjectProgressIntelligenceResponse,
)


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


def generate_project_progress_intelligence_ai(
    project_info: Dict[str, Any],
    stats: Dict[str, Any],
    task_breakdown: Dict[str, Any],
    provider: AIProvider,
) -> ProjectProgressIntelligenceResponse:
    """
    Generate evidence-based AI Project Progress Intelligence from project data and task statistics.
    """
    total_tasks = stats.get("total_tasks", 0)
    actual_progress = stats.get("average_task_progress", stats.get("average_progress", 0))

    # Empty state: Return clean response without invoking LLM
    if total_tasks == 0:
        return ProjectProgressIntelligenceResponse(
            project_summary="No project progress data available yet. Add tasks to generate project intelligence.",
            overall_progress=0,
            insights=[],
        )

    if not provider.is_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI service is not configured. Please configure an AI provider in backend settings.",
        )

    prompt = build_project_intelligence_prompt(project_info, stats, task_breakdown)

    try:
        raw_response = provider.complete(
            prompt=prompt,
            system_prompt=PROJECT_INTELLIGENCE_SYSTEM_PROMPT,
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
        validated = ProjectProgressIntelligenceResponse.model_validate(data)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="AI provider returned an invalid structured project intelligence response. Please try analyzing again.",
        )

    # Guarantee mathematical consistency with TaskForge's calculated progress
    validated.overall_progress = actual_progress

    return validated
