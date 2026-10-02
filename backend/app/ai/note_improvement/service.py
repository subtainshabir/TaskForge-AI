import json
import re
from typing import Optional

from fastapi import HTTPException, status

from app.ai.base import AIProvider
from app.ai.note_improvement.prompts import (
    NOTE_IMPROVEMENT_SYSTEM_PROMPT,
    build_note_improvement_prompt,
    clean_note_content_for_ai,
)
from app.ai.note_improvement.schemas import (
    NoteImprovementResponse,
)


def extract_json(raw_text: str) -> dict:
    """
    Extract and parse JSON object from LLM response text, handling markdown fences.
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


def improve_note_ai(
    title: str,
    content: Optional[str],
    provider: AIProvider,
) -> NoteImprovementResponse:
    """
    Review an existing note and suggest improvements to clarity, structure,
    grammar, conciseness, and organization using AI.
    Does NOT modify the note in the database.
    """
    if not provider.is_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI service is not configured. Please configure an AI provider in backend settings.",
        )

    clean_title = (title or "").strip()
    raw_content = content or ""
    clean_content = clean_note_content_for_ai(raw_content)

    # Empty / insufficient content check (Section 12)
    # Require at least some meaningful alphanumeric content to review
    has_meaningful_content = bool(
        clean_content
        and len(clean_content) >= 10
        and re.search(r"[a-zA-Z0-9]", clean_content)
    )

    if not has_meaningful_content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This note does not contain enough content to improve yet.",
        )

    is_html = bool(re.search(r"<[a-z][\s\S]*>", raw_content, re.IGNORECASE))

    prompt = build_note_improvement_prompt(
        title=clean_title,
        content=clean_content,
        is_html=is_html,
    )

    try:
        raw_response = provider.complete(
            prompt=prompt,
            system_prompt=NOTE_IMPROVEMENT_SYSTEM_PROMPT,
        )
    except HTTPException:
        raise
    except TimeoutError:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="AI service request timed out. Please try improving your note again.",
        )
    except Exception as e:
        err_msg = str(e).lower()
        if "401" in err_msg or "unauthorized" in err_msg:
            detail = "AI provider credentials rejected. Please verify backend settings."
        elif "429" in err_msg or "rate limit" in err_msg:
            detail = "AI provider rate limit exceeded. Please try again shortly."
        elif "timeout" in err_msg:
            detail = "AI service request timed out. Please try improving your note again."
        else:
            detail = "AI service encountered an unexpected error. Please try again."
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=detail,
        )

    try:
        data = extract_json(raw_response)
        validated = NoteImprovementResponse.model_validate(data)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="AI provider returned an invalid structured improvement response. Please try improving your note again.",
        )

    # Check if safe truncation limit added a warning
    if "[Content truncated for summarization due to length limit]" in clean_content:
        if not any("truncated" in w.lower() for w in validated.warnings):
            validated.warnings.append(
                "Note content was truncated due to input limits. Only the initial section was reviewed."
            )

    return validated
