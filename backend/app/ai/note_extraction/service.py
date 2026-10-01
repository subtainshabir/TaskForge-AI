import json
import re
from typing import Optional

from fastapi import HTTPException, status

from app.ai.base import AIProvider
from app.ai.note_extraction.prompts import (
    NOTE_EXTRACTION_SYSTEM_PROMPT,
    build_note_extraction_prompt,
    clean_note_content_for_ai,
)
from app.ai.note_extraction.schemas import NoteExtractionResponse


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


def extract_note_ai(
    title: str,
    content: Optional[str],
    provider: AIProvider,
) -> NoteExtractionResponse:
    """
    Extract structured information from note content (action items, decisions, facts,
    dates, people, tech terms, follow-ups) using AI without modifying the note.
    """
    if not provider.is_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI service is not configured. Please configure an AI provider in backend settings.",
        )

    clean_title = (title or "").strip()
    clean_content = clean_note_content_for_ai(content or "")

    # Empty or very short note content handling
    # If content has no alphanumeric characters or is shorter than 15 chars, return empty extraction
    if not clean_content or len(clean_content) < 15 or not re.search(r"[a-zA-Z0-9]", clean_content):
        return NoteExtractionResponse()

    prompt = build_note_extraction_prompt(clean_title, clean_content)

    try:
        raw_response = provider.complete(
            prompt=prompt,
            system_prompt=NOTE_EXTRACTION_SYSTEM_PROMPT,
        )
    except HTTPException:
        raise
    except TimeoutError:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="AI service request timed out. Please try extracting again.",
        )
    except Exception as e:
        err_msg = str(e).lower()
        if "401" in err_msg or "unauthorized" in err_msg:
            detail = "AI provider credentials rejected. Please verify backend settings."
        elif "429" in err_msg or "rate limit" in err_msg:
            detail = "AI provider rate limit exceeded. Please try again shortly."
        elif "timeout" in err_msg:
            detail = "AI service request timed out. Please try extracting again."
        else:
            detail = "AI service encountered an unexpected error. Please try again."
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=detail,
        )

    try:
        data = extract_json(raw_response)
        validated = NoteExtractionResponse.model_validate(data)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="AI provider returned an invalid structured extraction response. Please try extracting again.",
        )

    return validated
