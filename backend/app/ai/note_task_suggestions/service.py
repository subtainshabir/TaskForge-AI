import difflib
import json
import re
import string
from typing import List, Optional, Set

from fastapi import HTTPException, status

from app.ai.base import AIProvider
from app.ai.note_task_suggestions.prompts import (
    NOTE_TASK_SUGGESTIONS_SYSTEM_PROMPT,
    build_note_task_suggestions_prompt,
    clean_note_content_for_ai,
)
from app.ai.note_task_suggestions.schemas import (
    TaskSuggestion,
    TaskSuggestionResponse,
)


def normalize_title(title: str) -> str:
    """
    Normalize title string for robust deterministic duplicate matching.
    """
    if not title:
        return ""
    # Strip leading numbering like "1. ", "1) ", bullets "- ", "* ", "[ ] ", "[x] "
    s = re.sub(r"^\d+[\.\)]\s*", "", title.strip())
    s = re.sub(r"^\[[\sxX]?\]\s*", "", s)
    s = re.sub(r"^[-*•]\s*", "", s)
    s = s.lower()
    # Remove punctuation
    s = s.translate(str.maketrans("", "", string.punctuation))
    # Normalize internal whitespace
    return " ".join(s.split())


def is_duplicate_task(candidate_title: str, existing_title: str, threshold: float = 0.8) -> bool:
    """
    Determine deterministically if candidate_title is duplicate or very similar to existing_title.
    Uses normalized exact match, word-set comparison, substring matching, and sequence similarity.
    """
    n1 = normalize_title(candidate_title)
    n2 = normalize_title(existing_title)
    if not n1 or not n2:
        return False
    if n1 == n2:
        return True

    words1 = set(n1.split())
    words2 = set(n2.split())
    if words1 and words1 == words2:
        return True

    # High overlap substring match if both are descriptive (length >= 8)
    if len(n1) >= 8 and len(n2) >= 8:
        if n1 in n2 or n2 in n1:
            return True

    # Difflib similarity ratio
    ratio = difflib.SequenceMatcher(None, n1, n2).ratio()
    return ratio >= threshold


def check_and_flag_duplicates(
    suggestions: List[TaskSuggestion],
    existing_tasks: List[str],
) -> List[TaskSuggestion]:
    """
    Deterministic duplicate checking against existing task titles and within the suggestion batch.
    Flags matching suggestions with is_duplicate=True and records the existing task title.
    """
    seen_in_batch: Set[str] = set()
    result: List[TaskSuggestion] = []

    for sug in suggestions:
        norm_sug = normalize_title(sug.title)
        if not norm_sug:
            continue

        # Check against existing tasks
        is_dup = False
        matched_existing: Optional[str] = None
        for ext in existing_tasks:
            if is_duplicate_task(sug.title, ext):
                is_dup = True
                matched_existing = ext
                break

        # Check against previous items in the same batch
        if not is_dup and norm_sug in seen_in_batch:
            is_dup = True
            matched_existing = sug.title

        seen_in_batch.add(norm_sug)

        sug.is_duplicate = is_dup
        sug.duplicate_task_title = matched_existing
        result.append(sug)

    return result


def extract_json(raw_text: str) -> dict:
    """
    Extract and parse JSON object from LLM response text.
    """
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


def suggest_tasks_from_note_ai(
    title: str,
    content: Optional[str],
    provider: AIProvider,
    existing_tasks: Optional[List[str]] = None,
    project_id: Optional[int] = None,
    project_name: Optional[str] = None,
) -> TaskSuggestionResponse:
    """
    Analyze note content and suggest actionable task candidates using AI.
    Performs deterministic duplicate detection against existing tasks.
    Does NOT modify the note or create tasks automatically.
    """
    if not provider.is_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI service is not configured. Please configure an AI provider in backend settings.",
        )

    clean_title = (title or "").strip()
    clean_content = clean_note_content_for_ai(content or "")

    # If content has no alphanumeric characters or is shorter than 15 chars, return empty suggestions
    if not clean_content or len(clean_content) < 15 or not re.search(r"[a-zA-Z0-9]", clean_content):
        return TaskSuggestionResponse(
            suggestions=[],
            project_id=project_id,
            project_name=project_name,
        )

    prompt = build_note_task_suggestions_prompt(
        title=clean_title,
        content=clean_content,
        existing_tasks=existing_tasks,
    )

    try:
        raw_response = provider.complete(
            prompt=prompt,
            system_prompt=NOTE_TASK_SUGGESTIONS_SYSTEM_PROMPT,
        )
    except HTTPException:
        raise
    except TimeoutError:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="AI service request timed out. Please try suggesting tasks again.",
        )
    except Exception as e:
        err_msg = str(e).lower()
        if "401" in err_msg or "unauthorized" in err_msg:
            detail = "AI provider credentials rejected. Please verify backend settings."
        elif "429" in err_msg or "rate limit" in err_msg:
            detail = "AI provider rate limit exceeded. Please try again shortly."
        elif "timeout" in err_msg:
            detail = "AI service request timed out. Please try suggesting tasks again."
        else:
            detail = "AI service encountered an unexpected error. Please try again."
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=detail,
        )

    try:
        data = extract_json(raw_response)
        validated = TaskSuggestionResponse.model_validate(data)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="AI provider returned an invalid structured suggestion response. Please try suggesting tasks again.",
        )

    # Perform deterministic duplicate detection against existing tasks
    if existing_tasks:
        validated.suggestions = check_and_flag_duplicates(
            suggestions=validated.suggestions,
            existing_tasks=existing_tasks,
        )

    validated.project_id = project_id
    validated.project_name = project_name

    return validated
