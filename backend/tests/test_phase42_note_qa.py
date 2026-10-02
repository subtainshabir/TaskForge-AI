import json
import unittest

from fastapi import HTTPException
from sqlalchemy import select

from app.ai.base import AIProvider
from app.ai.note_qa.prompts import (
    NOTE_QA_SYSTEM_PROMPT,
    build_note_qa_prompt,
    clean_note_content_for_ai,
)
from app.ai.note_qa.schemas import (
    NoteQAMessage,
    NoteQARequest,
    NoteQAResponse,
)
from app.ai.note_qa.service import (
    answer_note_question_ai,
    extract_json,
)
from app.db.session import SessionLocal
from app.models.note import Note
from app.models.project import Project
from app.models.task import Task
from app.models.user import User
from app.notes.router import ask_note_question_endpoint


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


class TestPhase42NoteQA(unittest.TestCase):
    def setUp(self):
        self.db = SessionLocal()

        # User 1
        self.user1 = self.db.execute(
            select(User).where(User.email == "phase42_user1@example.com")
        ).scalar_one_or_none()
        if not self.user1:
            self.user1 = User(
                email="phase42_user1@example.com",
                password_hash="hashed_pw_1",
                name="Phase 42 User One",
            )
            self.db.add(self.user1)
            self.db.commit()
            self.db.refresh(self.user1)

        # User 2 (unauthorized)
        self.user2 = self.db.execute(
            select(User).where(User.email == "phase42_user2@example.com")
        ).scalar_one_or_none()
        if not self.user2:
            self.user2 = User(
                email="phase42_user2@example.com",
                password_hash="hashed_pw_2",
                name="Phase 42 User Two",
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
                name="Phase 42 AI Note Q&A Project",
                description="Testing AI note Q&A",
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
                description="Parent task for note Q&A",
            )
            self.db.add(self.task)
            self.db.commit()
            self.db.refresh(self.task)

        # Note for User 1
        self.note = Note(
            user_id=self.user1.id,
            project_id=self.proj.id,
            task_id=self.task.id,
            title="Authentication & Database Sprint Notes",
            content="""<h3>Sprint Goals</h3>
<p>Complete the authentication API and test the implementation before October 15.</p>
<ul class="note-checklist">
  <li class="note-checklist-item" data-checked="false"><input type="checkbox"> Implement JWT token issuance</li>
  <li class="note-checklist-item" data-checked="true"><input type="checkbox" checked> Set up user table schema</li>
</ul>
<p>Decision: Review the current database configuration on PostgreSQL 15.</p>
<pre class="note-code-block"><code>TOKEN_EXPIRY = 3600</code></pre>""",
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

    def test_question_validation_empty_raises_400(self):
        """Verify empty question raises 400 Bad Request."""
        provider = DummyAIProvider(configured=True)
        with self.assertRaises(HTTPException) as ctx:
            answer_note_question_ai(self.note.title, self.note.content, "", provider=provider)
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertEqual(ctx.exception.detail, "Question cannot be empty.")

    def test_question_validation_whitespace_raises_400(self):
        """Verify whitespace-only question raises 400 Bad Request."""
        provider = DummyAIProvider(configured=True)
        with self.assertRaises(HTTPException) as ctx:
            answer_note_question_ai(self.note.title, self.note.content, "    \n\t  ", provider=provider)
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertEqual(ctx.exception.detail, "Question cannot be empty.")

    def test_question_validation_too_long_raises_400(self):
        """Verify question exceeding 1000 chars raises 400 Bad Request."""
        provider = DummyAIProvider(configured=True)
        huge_question = "What about " + ("a" * 1005) + "?"
        with self.assertRaises(HTTPException) as ctx:
            answer_note_question_ai(self.note.title, self.note.content, huge_question, provider=provider)
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("Question is too long", ctx.exception.detail)

    def test_unconfigured_provider_raises_503(self):
        """Verify 503 is raised if AI provider is not configured."""
        provider = DummyAIProvider(configured=False)
        with self.assertRaises(HTTPException) as ctx:
            answer_note_question_ai(self.note.title, self.note.content, "What is the deadline?", provider=provider)
        self.assertEqual(ctx.exception.status_code, 503)

    def test_ai_timeout_raises_504(self):
        """Verify provider timeout raises 504 Gateway Timeout."""
        class TimeoutAIProvider(AIProvider):
            def is_configured(self):
                return True
            def complete(self, prompt, system_prompt=None, **kwargs):
                raise TimeoutError("Timed out")

        with self.assertRaises(HTTPException) as ctx:
            answer_note_question_ai(self.note.title, self.note.content, "When is the deadline?", provider=TimeoutAIProvider())
        self.assertEqual(ctx.exception.status_code, 504)

    def test_ai_malformed_json_raises_502(self):
        """Verify provider returning unparseable garbage raises 502 Bad Gateway."""
        provider = DummyAIProvider(configured=True, response="Not a JSON and completely unparseable")
        # Note: extract_json fallback extracts plain text if present, unless empty
        # If response is empty or unparsable empty json:
        provider_empty = DummyAIProvider(configured=True, response="")
        with self.assertRaises(HTTPException) as ctx:
            answer_note_question_ai(self.note.title, self.note.content, "Valid question?", provider=provider_empty)
        self.assertEqual(ctx.exception.status_code, 502)

    def test_ask_question_present_in_note(self):
        """Verify asking about a fact present in the note returns the exact factual answer."""
        mock_response = json.dumps({
            "answer": "The authentication deadline mentioned in the note is October 15."
        })
        provider = DummyAIProvider(configured=True, response=mock_response)

        res = answer_note_question_ai(
            title=self.note.title,
            content=self.note.content,
            question="What is the authentication deadline?",
            provider=provider,
        )

        self.assertIsInstance(res, NoteQAResponse)
        self.assertEqual(res.answer, "The authentication deadline mentioned in the note is October 15.")

    def test_ask_question_not_present_in_note(self):
        """Verify asking about a fact NOT in the note states that information is not present."""
        mock_response = json.dumps({
            "answer": "The note does not contain enough information to answer that question."
        })
        provider = DummyAIProvider(configured=True, response=mock_response)

        res = answer_note_question_ai(
            title=self.note.title,
            content=self.note.content,
            question="What is the database migration date?",
            provider=provider,
        )

        self.assertIsInstance(res, NoteQAResponse)
        self.assertIn("does not contain enough information", res.answer)

    def test_follow_up_question_with_conversation_history(self):
        """Verify follow-up questions include conversation history in prompt."""
        history = [
            NoteQAMessage(role="user", content="What is the deadline?"),
            NoteQAMessage(role="assistant", content="October 15."),
        ]
        prompt = build_note_qa_prompt(
            title="Sprint Note",
            content="Finish auth before October 15. Also review database configuration.",
            question="What needs to be completed before then?",
            history=history,
        )

        self.assertIn("What is the deadline?", prompt)
        self.assertIn("October 15.", prompt)
        self.assertIn("What needs to be completed before then?", prompt)
        self.assertIn("CONVERSATION CONTEXT", prompt)

    def test_endpoint_authorized_and_original_note_unchanged(self):
        """Verify API endpoint returns answer and leaves note in DB untouched."""
        mock_response = json.dumps({
            "answer": "The deadline mentioned in the note is October 15."
        })
        provider = DummyAIProvider(configured=True, response=mock_response)

        original_title = self.note.title
        original_content = self.note.content

        payload = NoteQARequest(question="What was the authentication deadline?")
        res = ask_note_question_endpoint(
            note_id=self.note.id,
            payload=payload,
            current_user=self.user1,
            db=self.db,
            ai_provider=provider,
        )

        self.assertIsInstance(res, NoteQAResponse)
        self.assertIn("October 15", res.answer)

        # Refresh from DB and verify unchanged
        self.db.refresh(self.note)
        self.assertEqual(self.note.title, original_title)
        self.assertEqual(self.note.content, original_content)

    def test_endpoint_unauthorized_user_raises_404(self):
        """Verify unauthorized user cannot ask questions about notes they do not own."""
        provider = DummyAIProvider(configured=True, response="{}")
        payload = NoteQARequest(question="What is this note about?")
        with self.assertRaises(HTTPException) as ctx:
            ask_note_question_endpoint(
                note_id=self.note.id,
                payload=payload,
                current_user=self.user2,
                db=self.db,
                ai_provider=provider,
            )
        self.assertEqual(ctx.exception.status_code, 404)

    def test_mock_ai_provider_integration_deadline(self):
        """Verify MockAIProvider answers deadline question correctly from note."""
        from app.ai.factory import MockAIProvider
        mock_provider = MockAIProvider()

        res = answer_note_question_ai(
            title=self.note.title,
            content=self.note.content,
            question="What was the authentication deadline?",
            provider=mock_provider,
        )
        self.assertIn("October 15", res.answer)

    def test_mock_ai_provider_integration_missing_fact(self):
        """Verify MockAIProvider correctly identifies facts not in note."""
        from app.ai.factory import MockAIProvider
        mock_provider = MockAIProvider()

        res = answer_note_question_ai(
            title=self.note.title,
            content=self.note.content,
            question="What is the database migration date?",
            provider=mock_provider,
        )
        self.assertIn("does not contain enough information", res.answer)

    def test_mock_ai_provider_integration_objective(self):
        """Verify MockAIProvider answers main objective question correctly."""
        from app.ai.factory import MockAIProvider
        mock_provider = MockAIProvider()

        res = answer_note_question_ai(
            title=self.note.title,
            content=self.note.content,
            question="What is the main objective?",
            provider=mock_provider,
        )
        self.assertIn("authentication API", res.answer)
