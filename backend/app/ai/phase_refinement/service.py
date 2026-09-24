import json
import re
from typing import List

from fastapi import HTTPException, status

from app.ai.base import AIProvider
from app.ai.phase_refinement.prompts import (
    PHASE_REFINEMENT_SYSTEM_PROMPT,
    build_phase_refinement_prompt,
)
from app.ai.phase_refinement.schemas import PhaseRefinementResponse, PhaseRefinementSuggestion
from app.models.phase import Phase
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


def refine_task_phases_ai(
    task: Task,
    phases: List[Phase],
    provider: AIProvider,
) -> PhaseRefinementResponse:
    if not provider.is_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI service is not configured. Please configure an AI provider in backend settings.",
        )

    if not phases:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Task has no phases to refine. Please add or generate phases first.",
        )

    project_name = getattr(task, "project_name", None) or (
        task.project.name if getattr(task, "project", None) else None
    )

    prompt = build_phase_refinement_prompt(
        task_title=task.title,
        task_description=task.description,
        project_name=project_name,
        phases=phases,
    )

    try:
        raw_response = provider.complete(
            prompt=prompt,
            system_prompt=PHASE_REFINEMENT_SYSTEM_PROMPT,
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
        validated = PhaseRefinementResponse.model_validate(data)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="AI provider returned an invalid structured refinement output. Please try reviewing again.",
        )

    valid_phase_ids = {p.id for p in phases}
    filtered_suggestions: List[PhaseRefinementSuggestion] = []

    for idx, sug in enumerate(validated.suggestions):
        sug_id = sug.id or f"sug-{idx + 1}"
        sug.id = sug_id

        if sug.type == "add":
            if not sug.proposed_title and sug.title:
                sug.proposed_title = sug.title
            if not sug.proposed_description and sug.description:
                sug.proposed_description = sug.description

        if sug.phase_id is not None and sug.phase_id not in valid_phase_ids:
            continue

        filtered_suggestions.append(sug)

    validated.suggestions = filtered_suggestions
    return validated
