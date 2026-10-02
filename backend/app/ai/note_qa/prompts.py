from typing import List, Optional

from app.ai.note_qa.schemas import NoteQAMessage
from app.ai.note_summarization.prompts import clean_note_content_for_ai

NOTE_QA_SYSTEM_PROMPT = """You are TaskForge AI's Note Question & Answering Engine.
Your role is to answer a user's question accurately, factually, and concisely using ONLY the provided note's content.

CRITICAL RULES:
1. USE ONLY THE NOTE:
   - Answer using strictly information explicitly present in the provided note.
   - If the note does not contain enough information to answer the question, clearly state:
     "The note does not contain enough information to answer that question." (or explain concisely what is not mentioned, e.g. "The note does not mention a database migration date.")
   - NEVER use external knowledge, assumptions, or extrapolation beyond what is written in the note.
2. NO HALLUCINATION:
   - Do NOT invent facts, dates, people, requirements, decisions, tasks, or technical details.
   - If an explicit date, deadline, metric, or name is in the note, preserve it verbatim (e.g., if note states "October 15", never say "October 20").
3. CONCISE & DIRECT:
   - Answer the question directly and concisely without conversational filler.
   - If prior conversation context is provided, use it only to understand follow-up references or pronouns (e.g. "it", "then", "that"), but all factual answers must still originate strictly from the note.
4. JSON FORMAT ONLY:
   - Respond strictly with a single valid JSON object adhering to the schema below without commentary or markdown code fences.

JSON SCHEMA:
{
  "answer": "Direct, factual answer based strictly on the note's content."
}
"""


def build_note_qa_prompt(
    title: str,
    content: str,
    question: str,
    history: Optional[List[NoteQAMessage]] = None,
) -> str:
    """
    Format note title, content, prior conversation context, and question into a prompt.
    """
    lines = [
        f"NOTE TITLE: {title.strip()}",
        "",
        "NOTE CONTENT:",
        content if content else "[No additional content]",
        "",
    ]

    if history and len(history) > 0:
        lines.append("CONVERSATION CONTEXT (Previous exchanges in this session):")
        # Keep last 10 messages for follow-up context
        for msg in history[-10:]:
            role_label = "User" if msg.role == "user" else "AI"
            lines.append(f"{role_label}: {msg.content.strip()}")
        lines.append("")

    lines.extend([
        f"USER QUESTION: {question.strip()}",
        "",
        "INSTRUCTIONS:",
        "Answer the question directly and concisely using ONLY facts from the note. If the information is not present, explicitly state that the note does not contain enough information. Output in the required JSON schema format.",
    ])

    return "\n".join(lines)
