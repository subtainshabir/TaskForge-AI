import json
import re
from typing import List, Optional

from fastapi import HTTPException, status

from app.ai.base import AIProvider
from app.ai.note_qa.prompts import (
    NOTE_QA_SYSTEM_PROMPT,
    build_note_qa_prompt,
    clean_note_content_for_ai,
)
from app.ai.note_qa.schemas import (
    NoteQAMessage,
    NoteQAResponse,
)


def extract_json(raw_text: str) -> dict:
    """
    Extract and parse JSON object from LLM response text, with fallback for plain text answers.
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
            try:
                return json.loads(match.group(1))
            except Exception:
                pass
        # Fallback: if model returned direct text answer instead of json
        if cleaned:
            return {"answer": cleaned}
        raise ValueError("Could not parse JSON from AI response")


def answer_note_question_ai(
    title: str,
    content: Optional[str],
    question: str,
    conversation_history: Optional[List[NoteQAMessage]] = None,
    provider: Optional[AIProvider] = None,
) -> NoteQAResponse:
    """
    Answer a question using strictly the content of the provided note.
    Does NOT modify the note.
    """
    if provider is None or not provider.is_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI service is not configured. Please configure an AI provider in backend settings.",
        )

    # Question validation (Section 7)
    q = (question or "").strip()
    if not q:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Question cannot be empty.",
        )
    if len(q) > 1000:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Question is too long (maximum 1000 characters).",
        )

    clean_title = (title or "").strip()
    raw_content = content or ""
    clean_content = clean_note_content_for_ai(raw_content)

    # If note has neither title nor content, return factual statement
    if not clean_title and not clean_content:
        return NoteQAResponse(
            answer="The note does not contain any content to answer questions from."
        )

    prompt = build_note_qa_prompt(
        title=clean_title,
        content=clean_content,
        question=q,
        history=conversation_history,
    )

    try:
        raw_response = provider.complete(
            prompt=prompt,
            system_prompt=NOTE_QA_SYSTEM_PROMPT,
        )
    except HTTPException:
        raise
    except TimeoutError:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="AI service request timed out. Please try asking your question again.",
        )
    except Exception as e:
        err_msg = str(e).lower()
        if "401" in err_msg or "unauthorized" in err_msg:
            detail = "AI provider credentials rejected. Please verify backend settings."
        elif "429" in err_msg or "rate limit" in err_msg:
            detail = "AI provider rate limit exceeded. Please try again shortly."
        elif "timeout" in err_msg:
            detail = "AI service request timed out. Please try asking your question again."
        else:
            detail = "AI service encountered an unexpected error. Please try again."
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=detail,
        )

    try:
        data = extract_json(raw_response)
        validated = NoteQAResponse.model_validate(data)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="AI provider returned an invalid structured Q&A response. Please try asking your question again.",
        )

    return validated
