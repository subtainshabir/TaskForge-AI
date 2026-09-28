import html
import re

MAX_NOTE_INPUT_CHARS = 12000

NOTE_SUMMARIZATION_SYSTEM_PROMPT = """You are TaskForge AI's Note Summarization Engine.
Your role is to analyze a user's productivity note and return a concise, high-value structured summary.

CRITICAL GUIDELINES:
1. FACT-BASED ONLY: Summarize ONLY information explicitly present in the note. Never invent facts, assume external context, or extrapolate beyond what is written.
2. PRESERVE TECHNICAL DETAILS: Maintain important technical terms, architectures, constraints, configuration values, and metrics.
3. IDENTIFY ACTION ITEMS: Extract clear actionable items, to-dos, checklists, and next steps present in the note. If no action items exist, return an empty list.
4. IMPORTANT DETAILS: Identify deadlines, dates, references, architectural choices, or warnings.
5. CONCISE & OBJECTIVE: The summary should be a clean 1-3 sentence synthesis. Avoid filler phrases like "This note discusses...".
6. DO NOT USE EXTERNAL KNOWLEDGE: Ignore external assumptions.
7. JSON OUTPUT ONLY: You must respond strictly with a valid JSON object matching the required schema.

JSON SCHEMA:
{
  "summary": "1-3 sentence objective overview of the note's purpose and contents.",
  "key_points": [
    "First major point or takeaway",
    "Second major point or takeaway"
  ],
  "action_items": [
    "First actionable step or to-do item",
    "Second actionable step or to-do item"
  ],
  "important_details": [
    "Important metric, configuration, deadline, or constraint"
  ]
}
"""


def clean_note_content_for_ai(raw_content: str) -> str:
    """
    Clean and normalize note content (HTML or plain text) for AI summarization.
    Preserves checklist states, headings, bullet lists, code blocks, and links,
    while removing styling and HTML artifacts.
    """
    if not raw_content or not raw_content.strip():
        return ""

    text = raw_content

    # If it contains HTML tags, convert structured elements into plain text formatting
    if re.search(r"<[a-z][\s\S]*>", text, re.IGNORECASE):
        # 1. Checklist items: [x] or [ ]
        text = re.sub(
            r'<li[^>]*data-checked="true"[^>]*>(?:<input[^>]*>)?\s*(.*?)(?=</li>)',
            r"- [x] \1",
            text,
            flags=re.IGNORECASE | re.DOTALL,
        )
        text = re.sub(
            r'<li[^>]*data-checked="false"[^>]*>(?:<input[^>]*>)?\s*(.*?)(?=</li>)',
            r"- [ ] \1",
            text,
            flags=re.IGNORECASE | re.DOTALL,
        )
        text = re.sub(
            r'<input[^>]*type="checkbox"[^>]*checked[^>]*>\s*',
            "[x] ",
            text,
            flags=re.IGNORECASE,
        )
        text = re.sub(
            r'<input[^>]*type="checkbox"[^>]*>\s*',
            "[ ] ",
            text,
            flags=re.IGNORECASE,
        )

        # 2. Code blocks
        text = re.sub(
            r'<pre[^>]*><code[^>]*>(.*?)</code></pre>',
            r"\n```\n\1\n```\n",
            text,
            flags=re.IGNORECASE | re.DOTALL,
        )

        # 3. Headings
        text = re.sub(
            r'<h[1-6][^>]*>(.*?)</h[1-6]>',
            r"\n\n# \1\n",
            text,
            flags=re.IGNORECASE | re.DOTALL,
        )

        # 4. Blockquotes
        text = re.sub(
            r'<blockquote[^>]*>(.*?)</blockquote>',
            r"\n> \1\n",
            text,
            flags=re.IGNORECASE | re.DOTALL,
        )

        # 5. List items
        text = re.sub(
            r'<li[^>]*>(.*?)</li>',
            r"- \1\n",
            text,
            flags=re.IGNORECASE | re.DOTALL,
        )

        # 6. Links: text (url)
        text = re.sub(
            r'<a[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>',
            r"\2 (\1)",
            text,
            flags=re.IGNORECASE | re.DOTALL,
        )

        # 7. Breaks and paragraphs
        text = re.sub(r'<br\s*/?>', "\n", text, flags=re.IGNORECASE)
        text = re.sub(r'</p>', "\n\n", text, flags=re.IGNORECASE)

        # 8. Strip all remaining HTML tags
        text = re.sub(r'<[^>]+>', " ", text)

        # 9. Decode HTML entities
        text = html.unescape(text)

    # Collapse excessive blank lines
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = text.strip()

    # Truncate if larger than max safe input
    if len(text) > MAX_NOTE_INPUT_CHARS:
        text = text[:MAX_NOTE_INPUT_CHARS] + "\n\n[Content truncated for summarization due to length limit]"

    return text


def build_note_summarization_prompt(title: str, content: str) -> str:
    """
    Format note title and cleaned content into a clear summarization prompt.
    """
    lines = [
        f"NOTE TITLE: {title.strip()}",
        "",
        "NOTE CONTENT:",
        content if content else "[No additional content]",
        "",
        "INSTRUCTIONS:",
        "Please analyze the above note and provide an accurate, structured summary in JSON following the system prompt schema.",
    ]
    return "\n".join(lines)
