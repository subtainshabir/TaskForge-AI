import json
import unittest

from fastapi import HTTPException
from sqlalchemy import select

from app.ai.base import AIProvider
from app.ai.note_extraction.prompts import clean_note_content_for_ai
from app.ai.note_extraction.schemas import ActionItem, ExtractedDate, NoteExtractionResponse
from app.ai.note_extraction.service import extract_note_ai
from app.db.session import SessionLocal
from app.models.note import Note
from app.models.project import Project
from app.models.user import User
from app.notes.router import extract_note_endpoint


class DummyAIProvider(AIProvider):
    def __init__(self, configured: bool = True, response: str = ""):
        self._configured = configured
        self._response = response

    def is_configured(self) -> bool:
        return self._configured

    def complete(self, prompt: str, system_prompt: str = None, **kwargs) -> str:
        if not self._configured:
            raise RuntimeError("Provider not configured")
        return self._response


class TestPhase39NoteExtraction(unittest.TestCase):
    def setUp(self):
        self.db = SessionLocal()

        # User 1
        self.user1 = self.db.execute(
            select(User).where(User.email == "phase39_user1@example.com")
        ).scalar_one_or_none()
        if not self.user1:
            self.user1 = User(
                email="phase39_user1@example.com",
                password_hash="hashed_pw_1",
                name="Phase 39 User One",
            )
            self.db.add(self.user1)
            self.db.commit()
            self.db.refresh(self.user1)

        # User 2 (unauthorized attacker)
        self.user2 = self.db.execute(
            select(User).where(User.email == "phase39_user2@example.com")
        ).scalar_one_or_none()
        if not self.user2:
            self.user2 = User(
                email="phase39_user2@example.com",
                password_hash="hashed_pw_2",
                name="Phase 39 User Two",
            )
            self.db.add(self.user2)
            self.db.commit()
            self.db.refresh(self.user2)

        # Project for User 1
        self.proj = self.db.execute(
            select(Project).where(Project.user_id == self.user1.id)
        ).scalars().first()
        if not self.proj:
            self.proj = Project(
                user_id=self.user1.id,
                name="Phase 39 Project",
                description="Testing AI note extraction",
            )
            self.db.add(self.proj)
            self.db.commit()
            self.db.refresh(self.proj)

        # Note for User 1
        self.note = Note(
            user_id=self.user1.id,
            project_id=self.proj.id,
            title="Backend Kickoff & Architecture Notes",
            content="""<h2>Architecture Decision Record</h2>
<p>We decided to use <b>PostgreSQL</b> as our primary database and <b>FastAPI</b> for the backend.</p>
<p>Lead architect Alice confirmed JWT token expiration will be 30 minutes.</p>
<ul class="note-checklist">
  <li class="note-checklist-item" data-checked="false"><input type="checkbox"> Implement authentication endpoints [Urgent]</li>
  <li class="note-checklist-item" data-checked="true"><input type="checkbox" checked> Set up Docker Compose</li>
</ul>
<blockquote>Target release date discussed was October 15.</blockquote>
<pre class="note-code-block"><code>DATABASE_URL = postgresql+psycopg://...</code></pre>
<p>Follow-up: Investigate Redis for session caching before next milestone.</p>""",
        )
        self.db.add(self.note)
        self.db.commit()
        self.db.refresh(self.note)

    def tearDown(self):
        note_to_del = self.db.execute(
            select(Note).where(Note.id == self.note.id)
        ).scalar_one_or_none()
        if note_to_del:
            self.db.delete(note_to_del)
            self.db.commit()
        self.db.close()

    def test_clean_content_for_extraction(self):
        raw_html = """
        <h2>Meeting Summary</h2>
        <ul class="note-checklist">
            <li class="note-checklist-item" data-checked="false"><input type="checkbox"> Item 1</li>
            <li class="note-checklist-item" data-checked="true"><input type="checkbox" checked> Item 2</li>
        </ul>
        <pre><code>val = 42</code></pre>
        <p><a href="https://example.com">Documentation</a></p>
        """
        cleaned = clean_note_content_for_ai(raw_html)
        self.assertIn("# Meeting Summary", cleaned)
        self.assertIn("- [ ] Item 1", cleaned)
        self.assertIn("- [x] Item 2", cleaned)
        self.assertIn("```", cleaned)
        self.assertIn("val = 42", cleaned)
        self.assertIn("Documentation (https://example.com)", cleaned)
        self.assertNotIn("<h2>", cleaned)

    def test_extract_empty_or_whitespace_note(self):
        provider = DummyAIProvider(configured=True)
        # Empty string
        res1 = extract_note_ai("Empty", "", provider)
        self.assertIsInstance(res1, NoteExtractionResponse)
        self.assertEqual(len(res1.action_items), 0)
        self.assertEqual(len(res1.decisions), 0)

        # Whitespace and punctuation only
        res2 = extract_note_ai("Whitespace", "    \n   ---   ", provider)
        self.assertIsInstance(res2, NoteExtractionResponse)
        self.assertEqual(len(res2.action_items), 0)
        self.assertEqual(len(res2.important_facts), 0)

    def test_extract_unconfigured_provider(self):
        provider = DummyAIProvider(configured=False)
        with self.assertRaises(HTTPException) as ctx:
            extract_note_ai("Title", "Some valid long content for extraction testing.", provider)
        self.assertEqual(ctx.exception.status_code, 503)

    def test_extract_valid_response(self):
        mock_payload = {
            "action_items": [
                {
                    "title": "Implement authentication endpoints",
                    "details": "JWT based endpoints",
                    "priority": "high",
                }
            ],
            "decisions": [
                "Use PostgreSQL as primary database",
                "Use FastAPI for backend",
            ],
            "important_facts": [
                "JWT token expiration set to 30 minutes",
            ],
            "dates": [
                {
                    "text": "October 15",
                    "date": None,
                    "context": "Target release date",
                }
            ],
            "people": [
                "Alice (Lead Architect)",
            ],
            "technical_terms": [
                "PostgreSQL",
                "FastAPI",
                "JWT",
                "Docker Compose",
            ],
            "follow_ups": [
                "Investigate Redis for session caching before next milestone",
            ],
        }
        provider = DummyAIProvider(configured=True, response=json.dumps(mock_payload))
        res = extract_note_ai(self.note.title, self.note.content, provider)

        self.assertIsInstance(res, NoteExtractionResponse)
        self.assertEqual(len(res.action_items), 1)
        self.assertEqual(res.action_items[0].title, "Implement authentication endpoints")
        self.assertEqual(res.action_items[0].priority, "high")
        self.assertEqual(len(res.decisions), 2)
        self.assertIn("Use PostgreSQL as primary database", res.decisions)
        self.assertEqual(len(res.important_facts), 1)
        self.assertEqual(len(res.dates), 1)
        self.assertEqual(res.dates[0].text, "October 15")
        self.assertIsNone(res.dates[0].date)
        self.assertEqual(res.dates[0].context, "Target release date")
        self.assertEqual(len(res.people), 1)
        self.assertIn("PostgreSQL", res.technical_terms)
        self.assertEqual(len(res.follow_ups), 1)

    def test_extract_markdown_fenced_json(self):
        fenced_json = """```json
{
  "action_items": [{"title": "Review PR", "details": null, "priority": null}],
  "decisions": ["Approved v1 design"],
  "important_facts": [],
  "dates": [],
  "people": [],
  "technical_terms": [],
  "follow_ups": []
}
```"""
        provider = DummyAIProvider(configured=True, response=fenced_json)
        res = extract_note_ai(self.note.title, self.note.content, provider)
        self.assertEqual(len(res.action_items), 1)
        self.assertEqual(res.action_items[0].title, "Review PR")
        self.assertEqual(res.decisions, ["Approved v1 design"])

    def test_extract_invalid_json_handling(self):
        provider = DummyAIProvider(configured=True, response="Malformed output not JSON")
        with self.assertRaises(HTTPException) as ctx:
            extract_note_ai(self.note.title, self.note.content, provider)
        self.assertEqual(ctx.exception.status_code, 502)

    def test_extract_endpoint_success_and_no_modification(self):
        mock_payload = {
            "action_items": [{"title": "Setup DB", "details": None, "priority": "medium"}],
            "decisions": ["PostgreSQL selected"],
            "important_facts": [],
            "dates": [],
            "people": [],
            "technical_terms": ["PostgreSQL"],
            "follow_ups": [],
        }
        provider = DummyAIProvider(configured=True, response=json.dumps(mock_payload))

        original_content = self.note.content
        original_title = self.note.title

        res = extract_note_endpoint(
            note_id=self.note.id,
            current_user=self.user1,
            db=self.db,
            ai_provider=provider,
        )

        self.assertIsInstance(res, NoteExtractionResponse)
        self.assertEqual(len(res.action_items), 1)
        self.assertEqual(res.decisions[0], "PostgreSQL selected")

        # Crucial check: verify DB note is not modified
        self.db.refresh(self.note)
        self.assertEqual(self.note.content, original_content)
        self.assertEqual(self.note.title, original_title)

    def test_extract_endpoint_unauthorized_user(self):
        provider = DummyAIProvider(configured=True)
        with self.assertRaises(HTTPException) as ctx:
            extract_note_endpoint(
                note_id=self.note.id,
                current_user=self.user2,  # User 2 does not own this note
                db=self.db,
                ai_provider=provider,
            )
        self.assertEqual(ctx.exception.status_code, 404)

    def test_extract_endpoint_nonexistent_note(self):
        provider = DummyAIProvider(configured=True)
        with self.assertRaises(HTTPException) as ctx:
            extract_note_endpoint(
                note_id=8888888,
                current_user=self.user1,
                db=self.db,
                ai_provider=provider,
            )
        self.assertEqual(ctx.exception.status_code, 404)


if __name__ == "__main__":
    unittest.main()
