import json
import unittest

from fastapi import HTTPException
from sqlalchemy import select

from app.ai.base import AIProvider
from app.ai.note_improvement.prompts import (
    NOTE_IMPROVEMENT_SYSTEM_PROMPT,
    build_note_improvement_prompt,
    clean_note_content_for_ai,
)
from app.ai.note_improvement.schemas import (
    NoteImprovementChange,
    NoteImprovementResponse,
)
from app.ai.note_improvement.service import (
    extract_json,
    improve_note_ai,
)
from app.db.session import SessionLocal
from app.models.note import Note
from app.models.project import Project
from app.models.task import Task
from app.models.user import User
from app.notes.router import improve_note_endpoint
from app.notes.schemas import NoteUpdate
from app.notes.service import update_note


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


class TestPhase41NoteImprovement(unittest.TestCase):
    def setUp(self):
        self.db = SessionLocal()

        # User 1
        self.user1 = self.db.execute(
            select(User).where(User.email == "phase41_user1@example.com")
        ).scalar_one_or_none()
        if not self.user1:
            self.user1 = User(
                email="phase41_user1@example.com",
                password_hash="hashed_pw_1",
                name="Phase 41 User One",
            )
            self.db.add(self.user1)
            self.db.commit()
            self.db.refresh(self.user1)

        # User 2 (unauthorized)
        self.user2 = self.db.execute(
            select(User).where(User.email == "phase41_user2@example.com")
        ).scalar_one_or_none()
        if not self.user2:
            self.user2 = User(
                email="phase41_user2@example.com",
                password_hash="hashed_pw_2",
                name="Phase 41 User Two",
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
                name="Phase 41 Security & Auth",
                description="Testing AI note improvement",
            )
            self.db.add(self.proj)
            self.db.commit()
            self.db.refresh(self.proj)

        # Task in project
        self.task = self.db.execute(
            select(Task).where(Task.project_id == self.proj.id, Task.title == "Auth Architecture")
        ).scalar_one_or_none()
        if not self.task:
            self.task = Task(
                project_id=self.proj.id,
                user_id=self.user1.id,
                title="Auth Architecture",
                description="Parent task for note testing",
            )
            self.db.add(self.task)
            self.db.commit()
            self.db.refresh(self.task)

        # Note for User 1 attached to project and task
        self.note = Note(
            user_id=self.user1.id,
            project_id=self.proj.id,
            task_id=self.task.id,
            title="Auth and database notes",
            content="""Need finish auth API and test it before October 15. Also database configuration should be reviewed.""",
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

    def test_schema_category_normalization(self):
        """Verify NoteImprovementChange category validator normalizes variations."""
        c1 = NoteImprovementChange(category="clarity", description="Made intent clear")
        self.assertEqual(c1.category, "clarity")

        c2 = NoteImprovementChange(category="grammar and spelling", description="Fixed typo")
        self.assertEqual(c2.category, "grammar")

        c3 = NoteImprovementChange(category="formatting and structure", description="Added headers")
        self.assertEqual(c3.category, "structure")

        c4 = NoteImprovementChange(category="conciseness/brevity", description="Removed filler")
        self.assertEqual(c4.category, "conciseness")

        c5 = NoteImprovementChange(category="grouping and organization", description="Reordered items")
        self.assertEqual(c5.category, "organization")

        c6 = NoteImprovementChange(category=None, description="General change")
        self.assertEqual(c6.category, "clarity")

    def test_improve_note_unconfigured_provider(self):
        """Verify 503 is raised if AI provider is not configured."""
        provider = DummyAIProvider(configured=False)
        with self.assertRaises(HTTPException) as ctx:
            improve_note_ai("Title", "Some valid note content to improve", provider)
        self.assertEqual(ctx.exception.status_code, 503)
        self.assertIn("not configured", ctx.exception.detail)

    def test_improve_note_empty_content_raises_400(self):
        """Verify empty note content raises 400 Bad Request with specified message without calling AI."""
        provider = DummyAIProvider(configured=True, response="should not be called")
        with self.assertRaises(HTTPException) as ctx:
            improve_note_ai("Empty Note", "", provider)
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertEqual(ctx.exception.detail, "This note does not contain enough content to improve yet.")

    def test_improve_note_whitespace_or_too_short_raises_400(self):
        """Verify note with only symbols/whitespace raises 400."""
        provider = DummyAIProvider(configured=True, response="should not be called")
        with self.assertRaises(HTTPException) as ctx:
            improve_note_ai("Short", "   \n\t  ...   ", provider)
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertEqual(ctx.exception.detail, "This note does not contain enough content to improve yet.")

    def test_improve_note_malformed_json_raises_502(self):
        """Verify invalid structured response from provider raises 502 Bad Gateway."""
        provider = DummyAIProvider(configured=True, response="I cannot improve this note.")
        with self.assertRaises(HTTPException) as ctx:
            improve_note_ai(
                "Sprint Goals",
                "We need to deliver the security layer by end of month and review all components.",
                provider,
            )
        self.assertEqual(ctx.exception.status_code, 502)
        self.assertIn("invalid structured improvement response", ctx.exception.detail)

    def test_improve_note_ai_timeout_raises_504(self):
        """Verify timeout raises 504 Gateway Timeout."""
        class TimeoutAIProvider(AIProvider):
            def is_configured(self):
                return True
            def complete(self, prompt, system_prompt=None, **kwargs):
                raise TimeoutError("Request timed out")

        with self.assertRaises(HTTPException) as ctx:
            improve_note_ai(
                "Title",
                "Valid note content with more than ten characters.",
                TimeoutAIProvider(),
            )
        self.assertEqual(ctx.exception.status_code, 504)

    def test_improve_note_valid_response(self):
        """Verify structured output parsing, categories, and date preservation."""
        mock_response = json.dumps({
            "improved_title": "Authentication & Database Implementation Plan",
            "improved_content": "## Authentication\n\nComplete the authentication API and test the implementation before October 15.\n\n## Database\n\nReview the current database configuration.",
            "changes": [
                {
                    "category": "clarity",
                    "description": "Clarified the authentication requirement.",
                },
                {
                    "category": "structure",
                    "description": "Separated authentication and database work into distinct sections.",
                },
            ],
            "warnings": [],
        })
        provider = DummyAIProvider(configured=True, response=mock_response)

        result = improve_note_ai(
            title=self.note.title,
            content=self.note.content,
            provider=provider,
        )

        self.assertIsInstance(result, NoteImprovementResponse)
        self.assertEqual(result.improved_title, "Authentication & Database Implementation Plan")
        self.assertIn("October 15", result.improved_content)
        self.assertEqual(len(result.changes), 2)
        self.assertEqual(result.changes[0].category, "clarity")
        self.assertEqual(result.changes[1].category, "structure")
        self.assertEqual(len(result.warnings), 0)

    def test_endpoint_authorized_and_original_note_unchanged(self):
        """
        Verify POST /notes/{note_id}/ai/improve returns improvement
        and leaves original note in DB completely untouched.
        """
        mock_response = json.dumps({
            "improved_title": "Authentication Implementation Plan",
            "improved_content": "## Authentication\n\nComplete the auth API before October 15.",
            "changes": [
                {"category": "clarity", "description": "Clarified deliverables"},
            ],
            "warnings": [],
        })
        provider = DummyAIProvider(configured=True, response=mock_response)

        original_title = self.note.title
        original_content = self.note.content

        res = improve_note_endpoint(
            note_id=self.note.id,
            current_user=self.user1,
            db=self.db,
            ai_provider=provider,
        )

        self.assertIsInstance(res, NoteImprovementResponse)
        self.assertEqual(res.improved_title, "Authentication Implementation Plan")

        # Confirm note in DB is completely untouched
        self.db.refresh(self.note)
        self.assertEqual(self.note.title, original_title)
        self.assertEqual(self.note.content, original_content)

    def test_endpoint_unauthorized_user_raises_404(self):
        """Verify unauthorized user cannot improve another user's note."""
        provider = DummyAIProvider(configured=True, response="{}")
        with self.assertRaises(HTTPException) as ctx:
            improve_note_endpoint(
                note_id=self.note.id,
                current_user=self.user2,
                db=self.db,
                ai_provider=provider,
            )
        self.assertEqual(ctx.exception.status_code, 404)

    def test_apply_changes_using_existing_note_update_api(self):
        """
        Verify applying improvement via existing update API:
        - Updates title and content
        - Preserves user ownership
        - Preserves project association
        - Preserves task association
        - Updates updated_at
        """
        improved_title = "Authentication & Database Implementation Plan"
        improved_content = "## Authentication\n\nComplete auth API before October 15."

        payload = NoteUpdate(
            title=improved_title,
            content=improved_content,
        )

        updated_note = update_note(self.db, self.note, payload)

        self.assertEqual(updated_note.title, improved_title)
        self.assertEqual(updated_note.content, improved_content)
        self.assertEqual(updated_note.user_id, self.user1.id)
        self.assertEqual(updated_note.project_id, self.proj.id)
        self.assertEqual(updated_note.task_id, self.task.id)

    def test_rich_content_checklists_and_codeblocks_prompt(self):
        """Verify build_note_improvement_prompt handles rich HTML notes properly."""
        rich_html = """<h3>Sprint Checklist</h3>
<ul class="note-checklist">
  <li class="note-checklist-item" data-checked="false"><input type="checkbox"> Finish JWT auth before October 15</li>
</ul>
<pre class="note-code-block"><code>PORT = 8000</code></pre>"""
        prompt = build_note_improvement_prompt("Security Sprint", rich_html, is_html=True)
        self.assertIn("NOTE FORMAT: Rich HTML", prompt)
        self.assertIn("October 15", prompt)
        self.assertIn("PORT = 8000", prompt)

    def test_mock_ai_provider_integration(self):
        """Verify MockAIProvider from factory generates improvements matching requirements."""
        from app.ai.factory import MockAIProvider
        mock_provider = MockAIProvider()

        content = "Need finish auth API and test it before October 15. Also database configuration should be reviewed."
        res = improve_note_ai(
            title=self.note.title,
            content=content,
            provider=mock_provider,
        )

        self.assertIsInstance(res, NoteImprovementResponse)
        self.assertEqual(res.improved_title, "Authentication & Database Implementation Plan")
        self.assertIn("October 15", res.improved_content)
        self.assertGreater(len(res.changes), 0)
        categories = [c.category for c in res.changes]
        self.assertIn("clarity", categories)
        self.assertIn("structure", categories)
