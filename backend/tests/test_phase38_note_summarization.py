import json
import unittest
from unittest.mock import MagicMock

from fastapi import HTTPException
from sqlalchemy import select

from app.ai.base import AIProvider
from app.ai.note_summarization.prompts import clean_note_content_for_ai
from app.ai.note_summarization.schemas import NoteSummaryResponse
from app.ai.note_summarization.service import summarize_note_ai
from app.db.session import SessionLocal
from app.models.note import Note
from app.models.project import Project
from app.models.user import User
from app.notes.router import summarize_note_endpoint


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


class TestPhase38NoteSummarization(unittest.TestCase):
    def setUp(self):
        self.db = SessionLocal()

        # User 1
        self.user1 = self.db.execute(
            select(User).where(User.email == "phase38_user1@example.com")
        ).scalar_one_or_none()
        if not self.user1:
            self.user1 = User(
                email="phase38_user1@example.com",
                password_hash="hashed_pw_1",
                name="Phase 38 User One",
            )
            self.db.add(self.user1)
            self.db.commit()
            self.db.refresh(self.user1)

        # User 2 (unauthorized attacker)
        self.user2 = self.db.execute(
            select(User).where(User.email == "phase38_user2@example.com")
        ).scalar_one_or_none()
        if not self.user2:
            self.user2 = User(
                email="phase38_user2@example.com",
                password_hash="hashed_pw_2",
                name="Phase 38 User Two",
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
                name="Phase 38 AI Project",
                description="Testing AI note summarization",
            )
            self.db.add(self.proj)
            self.db.commit()
            self.db.refresh(self.proj)

        # Note for User 1
        self.note = Note(
            user_id=self.user1.id,
            project_id=self.proj.id,
            title="Architecture Review Notes",
            content="""<h2>System Architecture</h2>
<p>We are building an <b>event-driven microservices</b> architecture.</p>
<ul class="note-checklist">
  <li class="note-checklist-item" data-checked="false"><input type="checkbox"> Implement caching layer</li>
  <li class="note-checklist-item" data-checked="true"><input type="checkbox" checked> Set up connection pool</li>
</ul>
<blockquote>Low latency is critical.</blockquote>
<pre class="note-code-block"><code>CACHE_TTL = 300</code></pre>
<p><a href="https://example.com/docs">Documentation Link</a></p>""",
        )
        self.db.add(self.note)
        self.db.commit()
        self.db.refresh(self.note)

    def tearDown(self):
        # Clean up created note
        note_to_del = self.db.execute(
            select(Note).where(Note.id == self.note.id)
        ).scalar_one_or_none()
        if note_to_del:
            self.db.delete(note_to_del)
            self.db.commit()
        self.db.close()

    def test_clean_note_content_for_ai(self):
        html_input = """
        <h1>Project Roadmap</h1>
        <p>This is a <b>bold</b> plan.</p>
        <ul class="note-checklist">
            <li class="note-checklist-item" data-checked="false"><input type="checkbox"> Task One</li>
            <li class="note-checklist-item" data-checked="true"><input type="checkbox" checked> Task Two</li>
        </ul>
        <pre><code>console.log('hi');</code></pre>
        <a href="https://taskforge.ai">TaskForge</a>
        """
        cleaned = clean_note_content_for_ai(html_input)
        self.assertIn("# Project Roadmap", cleaned)
        self.assertIn("- [ ] Task One", cleaned)
        self.assertIn("- [x] Task Two", cleaned)
        self.assertIn("```", cleaned)
        self.assertIn("TaskForge (https://taskforge.ai)", cleaned)
        self.assertNotIn("<h1>", cleaned)
        self.assertNotIn("<p>", cleaned)

    def test_clean_note_content_truncation(self):
        huge_input = "word " * 4000  # 20,000 characters
        cleaned = clean_note_content_for_ai(huge_input)
        self.assertLessEqual(len(cleaned), 12500)
        self.assertIn("[Content truncated for summarization due to length limit]", cleaned)

    def test_summarize_note_ai_empty_content(self):
        provider = DummyAIProvider(configured=True)
        res = summarize_note_ai("Empty Scratchpad", "", provider)
        self.assertIsInstance(res, NoteSummaryResponse)
        self.assertIn("insufficient content", res.summary.lower())
        self.assertEqual(len(res.action_items), 0)

    def test_summarize_note_ai_unconfigured_provider(self):
        provider = DummyAIProvider(configured=False)
        with self.assertRaises(HTTPException) as ctx:
            summarize_note_ai("My Note", "Some valid long content for the note", provider)
        self.assertEqual(ctx.exception.status_code, 503)

    def test_summarize_note_ai_success(self):
        sample_ai_json = json.dumps({
            "summary": "The note outlines the event-driven microservices architecture.",
            "key_points": [
                "Event-driven architecture selected for low latency",
                "Connection pool is already established",
            ],
            "action_items": [
                "Implement caching layer with CACHE_TTL = 300",
            ],
            "important_details": [
                "CACHE_TTL set to 300 seconds",
                "Documentation at https://example.com/docs",
            ],
        })
        provider = DummyAIProvider(configured=True, response=sample_ai_json)
        res = summarize_note_ai(self.note.title, self.note.content, provider)

        self.assertIsInstance(res, NoteSummaryResponse)
        self.assertEqual(res.summary, "The note outlines the event-driven microservices architecture.")
        self.assertEqual(len(res.key_points), 2)
        self.assertEqual(len(res.action_items), 1)
        self.assertIn("CACHE_TTL", res.action_items[0])
        self.assertEqual(len(res.important_details), 2)

    def test_summarize_note_ai_markdown_codeblock_json(self):
        sample_ai_json = """```json
{
  "summary": "Summary inside markdown fence.",
  "key_points": ["Point A"],
  "action_items": [],
  "important_details": []
}
```"""
        provider = DummyAIProvider(configured=True, response=sample_ai_json)
        res = summarize_note_ai(self.note.title, self.note.content, provider)
        self.assertEqual(res.summary, "Summary inside markdown fence.")
        self.assertEqual(res.key_points, ["Point A"])

    def test_summarize_note_ai_invalid_json(self):
        provider = DummyAIProvider(configured=True, response="Not a JSON response")
        with self.assertRaises(HTTPException) as ctx:
            summarize_note_ai(self.note.title, self.note.content, provider)
        self.assertEqual(ctx.exception.status_code, 502)

    def test_summarize_note_endpoint_success_and_no_modification(self):
        sample_ai_json = json.dumps({
            "summary": "Valid architecture summary.",
            "key_points": ["Point 1"],
            "action_items": ["Action 1"],
            "important_details": ["Detail 1"],
        })
        provider = DummyAIProvider(configured=True, response=sample_ai_json)

        original_content = self.note.content
        original_title = self.note.title

        res = summarize_note_endpoint(
            note_id=self.note.id,
            current_user=self.user1,
            db=self.db,
            ai_provider=provider,
        )

        self.assertIsInstance(res, NoteSummaryResponse)
        self.assertEqual(res.summary, "Valid architecture summary.")

        # Confirm note in DB was NOT modified
        self.db.refresh(self.note)
        self.assertEqual(self.note.content, original_content)
        self.assertEqual(self.note.title, original_title)

    def test_summarize_note_endpoint_unauthorized_user(self):
        provider = DummyAIProvider(configured=True)
        with self.assertRaises(HTTPException) as ctx:
            summarize_note_endpoint(
                note_id=self.note.id,
                current_user=self.user2,  # User 2 does not own note
                db=self.db,
                ai_provider=provider,
            )
        self.assertEqual(ctx.exception.status_code, 404)

    def test_summarize_note_endpoint_nonexistent_note(self):
        provider = DummyAIProvider(configured=True)
        with self.assertRaises(HTTPException) as ctx:
            summarize_note_endpoint(
                note_id=9999999,
                current_user=self.user1,
                db=self.db,
                ai_provider=provider,
            )
        self.assertEqual(ctx.exception.status_code, 404)


if __name__ == "__main__":
    unittest.main()
