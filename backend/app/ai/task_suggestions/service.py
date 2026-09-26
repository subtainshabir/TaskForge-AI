import json
import re
import string
from typing import List, Set

from fastapi import HTTPException, status

from app.ai.base import AIProvider
from app.ai.task_suggestions.prompts import (
    TASK_SUGGESTIONS_SYSTEM_PROMPT,
    build_project_task_suggestions_prompt,
    build_task_level_suggestions_prompt,
)
from app.ai.task_suggestions.schemas import (
    TaskSuggestionItem,
    TaskSuggestionsResponse,
)
from app.models.project import Project
from app.models.task import Task


def normalize_title(title: str) -> str:
    if not title:
        return ""
    # Strip leading list indices or bullets like "1. ", "1) ", "- ", "* "
    s = re.sub(r"^\d+[\.\)]\s*", "", title.strip())
    s = re.sub(r"^[-*•]\s*", "", s)
    s = s.lower()
    # Remove punctuation
    s = s.translate(str.maketrans("", "", string.punctuation))
    # Normalize internal whitespace
    return " ".join(s.split())


def filter_duplicate_suggestions(
    suggestions: List[TaskSuggestionItem], existing_tasks: List[Task]
) -> List[TaskSuggestionItem]:
    existing_normalized: Set[str] = {
        normalize_title(t.title) for t in existing_tasks if t.title
    }
    seen_in_batch: Set[str] = set()
    filtered: List[TaskSuggestionItem] = []

    for sug in suggestions:
        norm = normalize_title(sug.title)
        if not norm:
            continue
        if norm in existing_normalized or norm in seen_in_batch:
            continue
        seen_in_batch.add(norm)
        filtered.append(sug)

    return filtered


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


def generate_project_task_suggestions(
    project: Project,
    tasks: List[Task],
    provider: AIProvider,
) -> TaskSuggestionsResponse:
    if not provider.is_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI service is not configured. Please configure an AI provider in backend settings.",
        )

    prompt = build_project_task_suggestions_prompt(project, tasks)

    try:
        raw_response = provider.complete(
            prompt=prompt,
            system_prompt=TASK_SUGGESTIONS_SYSTEM_PROMPT,
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
        validated = TaskSuggestionsResponse.model_validate(data)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="AI provider returned an invalid structured task suggestion response. Please try again.",
        )

    # Filter out duplicates against existing project tasks and within suggestions
    unique_suggestions = filter_duplicate_suggestions(validated.suggestions, tasks)
    return TaskSuggestionsResponse(suggestions=unique_suggestions)


def generate_task_related_suggestions(
    task: Task,
    project_tasks: List[Task],
    provider: AIProvider,
) -> TaskSuggestionsResponse:
    if not provider.is_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI service is not configured. Please configure an AI provider in backend settings.",
        )

    prompt = build_task_level_suggestions_prompt(task, project_tasks)

    try:
        raw_response = provider.complete(
            prompt=prompt,
            system_prompt=TASK_SUGGESTIONS_SYSTEM_PROMPT,
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
        validated = TaskSuggestionsResponse.model_validate(data)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="AI provider returned an invalid structured task suggestion response. Please try again.",
        )

    unique_suggestions = filter_duplicate_suggestions(validated.suggestions, project_tasks)
    return TaskSuggestionsResponse(suggestions=unique_suggestions)
