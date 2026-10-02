import json
import re
from typing import List, Optional, Set, Tuple

from fastapi import HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.ai.base import AIProvider
from app.ai.note_search.prompts import (
    NOTE_SEARCH_SYSTEM_PROMPT,
    build_note_search_prompt,
    clean_note_content_for_ai,
)
from app.ai.note_search.schemas import (
    NoteAISearchResponse,
    NoteSearchSource,
)
from app.models.note import Note

MAX_NOTES_FOR_AI = 5

STOP_WORDS: Set[str] = {
    "a", "about", "above", "after", "again", "against", "all", "am", "an",
    "and", "any", "are", "aren't", "as", "at", "be", "because", "been",
    "before", "being", "below", "between", "both", "but", "by", "can",
    "can't", "cannot", "could", "couldn't", "did", "didn't", "do", "does",
    "doesn't", "doing", "don't", "down", "during", "each", "few", "for",
    "from", "further", "had", "hadn't", "has", "hasn't", "have", "haven't",
    "having", "he", "her", "here", "hers", "herself", "him", "himself",
    "his", "how", "i", "if", "in", "into", "is", "isn't", "it", "it's",
    "its", "itself", "let's", "me", "more", "most", "my", "myself", "no",
    "nor", "not", "of", "off", "on", "once", "only", "or", "other", "ought",
    "our", "ours", "ourselves", "out", "over", "own", "same", "she", "should",
    "shouldn't", "so", "some", "such", "than", "that", "the", "their",
    "theirs", "them", "themselves", "then", "there", "these", "they", "this",
    "those", "through", "to", "too", "under", "until", "up", "very", "was",
    "wasn't", "we", "were", "weren't", "what", "when", "where", "which",
    "while", "who", "whom", "why", "with", "won't", "would", "wouldn't",
    "you", "your", "yours", "yourself", "yourselves",
    # Note domain stopwords
    "note", "notes", "mention", "mentions", "mentioned", "discuss",
    "discusses", "discussed", "tell", "show", "give", "find", "search",
    "look", "see", "contain", "contains", "contained",
}


def extract_search_keywords(question: str) -> Tuple[str, List[str]]:
    """
    Extract clean phrase and individual meaningful keywords from natural language question.
    """
    cleaned_phrase = re.sub(r"[^\w\s]", " ", question.lower()).strip()
    words = cleaned_phrase.split()
    meaningful = [w for w in words if len(w) >= 2 and w not in STOP_WORDS]
    if not meaningful:
        # Fallback to all words of length >= 2 if all were filtered by stop words
        meaningful = [w for w in words if len(w) >= 2]
    return cleaned_phrase, meaningful


def rank_note_relevance(
    note: Note,
    clean_phrase: str,
    keywords: List[str],
) -> float:
    """
    Calculate deterministic relevance score for a note against search terms.
    """
    title_lower = (note.title or "").lower()
    raw_content = note.content or ""
    content_lower = clean_note_content_for_ai(raw_content).lower()

    score = 0.0

    # Phrase matches (highest weight)
    if clean_phrase and len(clean_phrase) > 3:
        if clean_phrase in title_lower:
            score += 60.0
        if clean_phrase in content_lower:
            score += 35.0

    matched_kw_count = 0

    # Keyword matches
    for kw in keywords:
        kw_matched = False
        if kw in title_lower:
            score += 25.0
            kw_matched = True
            # Extra points for whole word match
            if re.search(rf"\b{re.escape(kw)}\b", title_lower):
                score += 10.0

        if kw in content_lower:
            kw_matched = True
            occurrences = len(re.findall(re.escape(kw), content_lower))
            score += min(occurrences * 5.0, 25.0)

        if kw_matched:
            matched_kw_count += 1

    # Keyword coverage bonus
    if keywords:
        coverage = matched_kw_count / len(keywords)
        score += coverage * 30.0

    # Recency tie-breaker
    if score > 0 and note.updated_at:
        score += note.updated_at.timestamp() / 1e12

    return score


def extract_json(raw_text: str) -> dict:
    """
    Extract and parse JSON object from LLM response text, with fallback.
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
        if cleaned:
            return {"answer": cleaned, "source_note_ids": []}
        raise ValueError("Could not parse JSON from AI response")


def search_notes_ai(
    db: Session,
    user_id: int,
    question: str,
    provider: Optional[AIProvider] = None,
) -> NoteAISearchResponse:
    """
    Perform Cross-Note AI Search:
    1. Validate query.
    2. Deterministically retrieve and rank user-owned notes.
    3. If no relevant notes found, return empty results without calling AI.
    4. Send top candidate notes to existing AI service.
    5. Return synthesized answer with cited source notes.
    """
    # 1. Query Validation
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

    # 2. Extract search terms
    clean_phrase, keywords = extract_search_keywords(q)

    # 3. Retrieve user-owned notes from DB (Strict ownership enforcement)
    base_query = select(Note).where(Note.user_id == user_id)

    filter_conditions = []
    if clean_phrase and len(clean_phrase) > 3:
        filter_conditions.append(Note.title.ilike(f"%{clean_phrase}%"))
        filter_conditions.append(Note.content.ilike(f"%{clean_phrase}%"))
    for kw in keywords:
        filter_conditions.append(Note.title.ilike(f"%{kw}%"))
        filter_conditions.append(Note.content.ilike(f"%{kw}%"))

    if filter_conditions:
        stmt = base_query.where(or_(*filter_conditions))
    else:
        stmt = base_query

    candidate_notes = list(db.execute(stmt).scalars().all())

    # Section 10: If no notes match, return immediately without calling AI
    if not candidate_notes:
        return NoteAISearchResponse(
            answer="No relevant notes were found.",
            sources=[],
        )

    # 4. Rank candidate notes deterministically
    scored_notes: List[Tuple[float, Note]] = []
    for note in candidate_notes:
        score = rank_note_relevance(note, clean_phrase, keywords)
        if score > 0:
            scored_notes.append((score, note))

    if not scored_notes:
        return NoteAISearchResponse(
            answer="No relevant notes were found.",
            sources=[],
        )

    # Sort descending by score and pick top N
    scored_notes.sort(key=lambda x: x[0], reverse=True)
    top_notes = [note for _, note in scored_notes[:MAX_NOTES_FOR_AI]]

    # 5. Check AI Provider configuration
    if provider is None or not provider.is_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI service is not configured. Please configure an AI provider in backend settings.",
        )

    # 6. Build prompt with normalized content
    notes_data: List[Tuple[int, str, str]] = []
    for note in top_notes:
        clean_content = clean_note_content_for_ai(note.content or "")
        notes_data.append((note.id, note.title, clean_content))

    prompt = build_note_search_prompt(question=q, notes_data=notes_data)

    # 7. Complete with AI Provider
    try:
        raw_response = provider.complete(
            prompt=prompt,
            system_prompt=NOTE_SEARCH_SYSTEM_PROMPT,
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

    # 8. Parse Response
    parsed = extract_json(raw_response)
    raw_answer = str(parsed.get("answer", "")).strip()
    if not raw_answer:
        raw_answer = "The available notes do not contain enough information to answer this question."

    raw_source_ids = parsed.get("source_note_ids", [])
    if not isinstance(raw_source_ids, list):
        raw_source_ids = []

    # If the answer indicates lack of information or no notes found, sources should be empty
    lower_ans = raw_answer.lower()
    if (
        "not contain enough information" in lower_ans
        or "no relevant notes" in lower_ans
        or "does not contain enough information" in lower_ans
    ):
        return NoteAISearchResponse(
            answer=raw_answer,
            sources=[],
        )

    # Map source IDs to actual valid top notes (prevents hallucinated source IDs)
    note_id_map = {n.id: n for n in top_notes}
    valid_sources: List[NoteSearchSource] = []
    seen_ids = set()

    for sid in raw_source_ids:
        try:
            int_id = int(sid)
            if int_id in note_id_map and int_id not in seen_ids:
                seen_ids.add(int_id)
                valid_sources.append(
                    NoteSearchSource(
                        note_id=int_id,
                        title=note_id_map[int_id].title,
                    )
                )
        except (ValueError, TypeError):
            continue

    # Fallback if AI answered but left source_note_ids empty:
    # If the answer explicitly references note titles or if only one note was retrieved, cite it
    if not valid_sources and len(top_notes) == 1:
        valid_sources.append(
            NoteSearchSource(note_id=top_notes[0].id, title=top_notes[0].title)
        )
    elif not valid_sources:
        for note in top_notes:
            if note.title.lower() in lower_ans and note.id not in seen_ids:
                seen_ids.add(note.id)
                valid_sources.append(
                    NoteSearchSource(note_id=note.id, title=note.title)
                )

    return NoteAISearchResponse(
        answer=raw_answer,
        sources=valid_sources,
    )
