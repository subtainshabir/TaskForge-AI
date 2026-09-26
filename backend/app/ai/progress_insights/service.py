import json
import re
from typing import Any, Dict

from fastapi import HTTPException, status

from app.ai.base import AIProvider
from app.ai.progress_insights.prompts import (
    PROGRESS_INSIGHTS_SYSTEM_PROMPT,
    build_progress_insights_prompt,
)
from app.ai.progress_insights.schemas import ProgressInsightsResponse


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


def generate_progress_insights_ai(
    analytics_data: Dict[str, Any],
    task_context: Dict[str, Any],
    provider: AIProvider,
) -> ProgressInsightsResponse:
    """
    Generate evidence-based AI Progress Insights from analytics and task context.
    """
    if not provider.is_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI service is not configured. Please configure an AI provider in backend settings.",
        )

    overview = analytics_data.get("overview", {})
    if overview.get("total_tasks", 0) == 0:
        return ProgressInsightsResponse(
            summary="Not enough task data for meaningful AI insights yet.",
            insights=[],
        )

    prompt = build_progress_insights_prompt(analytics_data, task_context)

    try:
        raw_response = provider.complete(
            prompt=prompt,
            system_prompt=PROGRESS_INSIGHTS_SYSTEM_PROMPT,
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
        validated = ProgressInsightsResponse.model_validate(data)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="AI provider returned an invalid structured progress insights response. Please try analyzing again.",
        )

    return validated
