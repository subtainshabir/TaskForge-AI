from typing import List, Tuple

from app.ai.note_summarization.prompts import clean_note_content_for_ai

MAX_CHARS_PER_NOTE = 3000

NOTE_SEARCH_SYSTEM_PROMPT = """You are TaskForge AI's Cross-Note Search Engine.
Your role is to answer a user's question accurately, factually, and concisely using ONLY the provided notes.

CRITICAL RULES:
1. USE ONLY THE PROVIDED NOTES:
   - Answer using strictly information explicitly present in the provided notes.
   - If the provided notes do not contain enough information to answer the question, clearly state:
     "The available notes do not contain enough information to answer this question." (or state concisely what is missing).
   - NEVER use external knowledge, assumptions, or extrapolation beyond what is written in the notes.
2. NO HALLUCINATION:
   - Do NOT invent facts, dates, people, requirements, decisions, tasks, or technical details.
   - If dates, deadlines, or technical names appear in the notes, preserve them verbatim.
3. SOURCE CITATIONS:
   - Identify which notes directly contributed facts to your answer by their Note ID.
   - Only cite Note IDs from the provided notes that actually contain relevant information used in the answer.
   - If the question cannot be answered from the notes, return an empty source list.
   - Do NOT cite notes that were not relevant to the final answer.
4. CONCISE & OBJECTIVE:
   - Keep the answer direct, clear, and focused on answering the user's question.
5. JSON FORMAT ONLY:
   - Respond strictly with a single valid JSON object adhering to the schema below without commentary or markdown code fences.

JSON SCHEMA:
{
  "answer": "Direct answer synthesizing facts from the relevant notes, or stating information is not present.",
  "source_note_ids": [12, 18]
}
"""


def build_note_search_prompt(
    question: str,
    notes_data: List[Tuple[int, str, str]],
) -> str:
    """
    Format user question and candidate notes (id, title, cleaned_content) into the LLM prompt.
    """
    lines = [
        f"USER QUESTION: {question.strip()}",
        "",
        "AVAILABLE CANDIDATE NOTES:",
    ]

    for note_id, title, content in notes_data:
        lines.append(f"--- NOTE ID: {note_id} | TITLE: {title.strip()} ---")
        sample_content = (content or "").strip()[:MAX_CHARS_PER_NOTE]
        lines.append(sample_content if sample_content else "[No additional content]")
        lines.append("")

    lines.extend([
        "INSTRUCTIONS:",
        "Answer the user's question using ONLY the provided notes above. Identify the source_note_ids of notes that directly support your answer. If the notes do not contain sufficient information, state 'The available notes do not contain enough information to answer this question.' and return an empty list for source_note_ids. Output strictly in the required JSON schema format.",
    ])

    return "\n".join(lines)
