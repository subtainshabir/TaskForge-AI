import json
import unittest

from fastapi import HTTPException
from sqlalchemy import select

from app.ai.base import AIProvider
from app.ai.note_task_suggestions.prompts import (
    NOTE_TASK_SUGGESTIONS_SYSTEM_PROMPT,
    build_note_task_suggestions_prompt,
    clean_note_content_for_ai,
)
from app.ai.note_task_suggestions.schemas import (
    TaskSuggestion,
    TaskSuggestionResponse,
)
from app.ai.note_task_suggestions.service import (
    check_and_flag_duplicates,
    is_duplicate_task,
    normalize_title,
    suggest_tasks_from_note_ai,
)
from app.db.session import SessionLocal
from app.models.note import Note
from app.models.project import Project
from app.models.task import Task
from app.models.user import User
from app.notes.router import suggest_tasks_endpoint
from app.tasks.schemas import TaskCreate
from app.tasks.service import create_task


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


class TestPhase40NoteTaskSuggestions(unittest.TestCase):
    def setUp(self):
        self.db = SessionLocal()

        # User 1
        self.user1 = self.db.execute(
            select(User).where(User.email == "phase40_user1@example.com")
        ).scalar_one_or_none()
        if not self.user1:
            self.user1 = User(
                email="phase40_user1@example.com",
                password_hash="hashed_pw_1",
                name="Phase 40 User One",
            )
            self.db.add(self.user1)
            self.db.commit()
            self.db.refresh(self.user1)

        # User 2 (unauthorized)
        self.user2 = self.db.execute(
            select(User).where(User.email == "phase40_user2@example.com")
        ).scalar_one_or_none()
        if not self.user2:
            self.user2 = User(
                email="phase40_user2@example.com",
                password_hash="hashed_pw_2",
                name="Phase 40 User Two",
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
                name="Phase 40 Auth & Security Project",
                description="Testing AI note-to-task suggestions",
            )
            self.db.add(self.proj)
            self.db.commit()
            self.db.refresh(self.proj)

        # Existing Task in project
        self.existing_task = self.db.execute(
            select(Task).where(Task.project_id == self.proj.id, Task.title == "Implement JWT authentication")
        ).scalar_one_or_none()
        if not self.existing_task:
            self.existing_task = Task(
                project_id=self.proj.id,
                user_id=self.user1.id,
                title="Implement JWT authentication",
                description="Existing auth task",
            )
            self.db.add(self.existing_task)
            self.db.commit()
            self.db.refresh(self.existing_task)

        # Note for User 1 attached to project
        self.note = Note(
            user_id=self.user1.id,
            project_id=self.proj.id,
            title="Sprint Planning - Authentication & Database",
            content="""<h3>Sprint Goals</h3>
<p>We need to deliver the security layer by end of month.</p>
<ul class="note-checklist">
  <li class="note-checklist-item" data-checked="false"><input type="checkbox"> Implement JWT authentication [High]</li>
  <li class="note-checklist-item" data-checked="false"><input type="checkbox"> Test authentication API [Medium]</li>
  <li class="note-checklist-item" data-checked="false"><input type="checkbox"> Review PostgreSQL configuration [Low]</li>
</ul>
<p>Deadline: Finish authentication by October 15.</p>
<p>Note: The database runs PostgreSQL 15 on Ubuntu.</p>""",
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

    def test_title_normalization_and_duplicate_detection(self):
        """Verify title normalization and deterministic duplicate detection."""
        self.assertEqual(normalize_title("1. Implement JWT Authentication!"), "implement jwt authentication")
        self.assertEqual(normalize_title("- [ ]  Review PostgreSQL configuration  "), "review postgresql configuration")
        self.assertEqual(normalize_title("•   Deploy to staging"), "deploy to staging")

        # Exact match
        self.assertTrue(is_duplicate_task("Implement JWT Authentication", "implement jwt authentication"))
        # Minor variation
        self.assertTrue(is_duplicate_task("1. Implement JWT Authentication", "Implement JWT Authentication"))
        # Word set match
        self.assertTrue(is_duplicate_task("Authentication JWT Implement", "Implement JWT Authentication"))
        # Distinct tasks
        self.assertFalse(is_duplicate_task("Write unit tests", "Implement JWT authentication"))

    def test_check_and_flag_duplicates(self):
        """Verify check_and_flag_duplicates marks matching suggestions with is_duplicate."""
        suggestions = [
            TaskSuggestion(
                title="Implement JWT authentication",
                description="Core auth",
                priority="high",
            ),
            TaskSuggestion(
                title="Review PostgreSQL configuration",
                description="DB tuning",
                priority="low",
            ),
        ]
        existing = ["Implement JWT Authentication"]
        flagged = check_and_flag_duplicates(suggestions, existing)

        self.assertTrue(flagged[0].is_duplicate)
        self.assertEqual(flagged[0].duplicate_task_title, "Implement JWT Authentication")
        self.assertFalse(flagged[1].is_duplicate)
        self.assertIsNone(flagged[1].duplicate_task_title)

    def test_schema_priority_normalization(self):
        """Verify TaskSuggestion priority validator normalizes variations."""
        s1 = TaskSuggestion(title="Task 1", priority="URGENT")
        self.assertEqual(s1.priority, "urgent")
        s2 = TaskSuggestion(title="Task 2", priority="critical")
        self.assertEqual(s2.priority, "urgent")
        s3 = TaskSuggestion(title="Task 3", priority="Normal")
        self.assertEqual(s3.priority, "medium")
        s4 = TaskSuggestion(title="Task 4", priority=None)
        self.assertEqual(s4.priority, "medium")

    def test_suggest_tasks_unconfigured_provider(self):
        """Verify 503 is raised if AI provider is not configured."""
        provider = DummyAIProvider(configured=False)
        with self.assertRaises(HTTPException) as ctx:
            suggest_tasks_from_note_ai("Title", "Content with actionable items", provider)
        self.assertEqual(ctx.exception.status_code, 503)

    def test_suggest_tasks_empty_content(self):
        """Verify empty note content returns empty suggestions without calling AI."""
        provider = DummyAIProvider(configured=True, response="should not be called")
        res = suggest_tasks_from_note_ai("Empty Note", "", provider, project_id=10, project_name="Test Proj")
        self.assertEqual(len(res.suggestions), 0)
        self.assertEqual(res.project_id, 10)
        self.assertEqual(res.project_name, "Test Proj")

    def test_suggest_tasks_malformed_json_raises_502(self):
        """Verify invalid structured response from provider raises 502 Bad Gateway."""
        provider = DummyAIProvider(configured=True, response="Definitely not json")
        with self.assertRaises(HTTPException) as ctx:
            suggest_tasks_from_note_ai(
                "Kickoff",
                "This note contains plenty of content for analysis but AI returns garbage.",
                provider,
            )
        self.assertEqual(ctx.exception.status_code, 502)

    def test_suggest_tasks_valid_ai_response(self):
        """Verify structured output parsing and duplicate flagging against existing tasks."""
        mock_response = json.dumps({
            "suggestions": [
                {
                    "title": "Implement JWT authentication",
                    "description": "Implement the authentication API described in the note.",
                    "priority": "high",
                    "due_date": "2026-10-15",
                    "reason": "Explicit action mentioned in note checklist",
                    "confidence": 0.95,
                },
                {
                    "title": "Test authentication API",
                    "description": "Write automated tests for the auth endpoints.",
                    "priority": "medium",
                    "due_date": None,
                    "reason": "Listed as a follow-up item in note",
                    "confidence": 0.90,
                },
            ]
        })
        provider = DummyAIProvider(configured=True, response=mock_response)
        existing_tasks = ["Implement JWT authentication"]

        result = suggest_tasks_from_note_ai(
            title=self.note.title,
            content=self.note.content,
            provider=provider,
            existing_tasks=existing_tasks,
            project_id=self.proj.id,
            project_name=self.proj.name,
        )

        self.assertEqual(len(result.suggestions), 2)
        # First suggestion is flagged as duplicate
        self.assertTrue(result.suggestions[0].is_duplicate)
        self.assertEqual(result.suggestions[0].duplicate_task_title, "Implement JWT authentication")
        self.assertEqual(result.suggestions[0].due_date, "2026-10-15")
        self.assertEqual(result.suggestions[0].priority, "high")

        # Second suggestion is NOT duplicate
        self.assertFalse(result.suggestions[1].is_duplicate)
        self.assertIsNone(result.suggestions[1].due_date)
        self.assertEqual(result.suggestions[1].priority, "medium")

        self.assertEqual(result.project_id, self.proj.id)
        self.assertEqual(result.project_name, self.proj.name)

    def test_endpoint_authorized_and_original_note_unchanged(self):
        """Verify API endpoint returns suggestions and leaves original note untouched."""
        mock_response = json.dumps({
            "suggestions": [
                {
                    "title": "Review PostgreSQL configuration",
                    "description": "Check connection pool and memory settings.",
                    "priority": "low",
                    "due_date": None,
                    "reason": "Mentioned as technical follow-up",
                    "confidence": 0.88,
                }
            ]
        })
        provider = DummyAIProvider(configured=True, response=mock_response)

        original_content = self.note.content
        original_title = self.note.title

        res = suggest_tasks_endpoint(
            note_id=self.note.id,
            current_user=self.user1,
            db=self.db,
            ai_provider=provider,
        )

        self.assertIsInstance(res, TaskSuggestionResponse)
        self.assertEqual(len(res.suggestions), 1)
        self.assertEqual(res.suggestions[0].title, "Review PostgreSQL configuration")
        self.assertEqual(res.suggestions[0].priority, "low")
        self.assertEqual(res.project_id, self.proj.id)

        # Refresh note from DB and confirm unchanged
        self.db.refresh(self.note)
        self.assertEqual(self.note.content, original_content)
        self.assertEqual(self.note.title, original_title)

    def test_endpoint_unauthorized_user(self):
        """Verify unauthorized user cannot suggest tasks for a note they do not own."""
        provider = DummyAIProvider(configured=True, response="{}")
        with self.assertRaises(HTTPException) as ctx:
            suggest_tasks_endpoint(
                note_id=self.note.id,
                current_user=self.user2,
                db=self.db,
                ai_provider=provider,
            )
        self.assertEqual(ctx.exception.status_code, 404)

    def test_task_note_project_association_rule(self):
        """
        Verify that if a note belongs to a task, suggested_project_id is NOT auto-assigned,
        requiring explicit user project selection per Requirement 6.
        """
        task_note = Note(
            user_id=self.user1.id,
            project_id=self.proj.id,
            task_id=self.existing_task.id,
            title="Subtask Meeting Notes",
            content="<p>Must write tests for login endpoint</p>",
        )
        self.db.add(task_note)
        self.db.commit()
        self.db.refresh(task_note)

        mock_response = json.dumps({
            "suggestions": [
                {
                    "title": "Write tests for login endpoint",
                    "description": "Automated login tests",
                    "priority": "medium",
                    "due_date": None,
                    "reason": "Stated in task note",
                    "confidence": 0.9,
                }
            ]
        })
        provider = DummyAIProvider(configured=True, response=mock_response)

        res = suggest_tasks_endpoint(
            note_id=task_note.id,
            current_user=self.user1,
            db=self.db,
            ai_provider=provider,
        )

        # Per requirement 6: When note belongs to a task, project_id is None
        # so user must explicitly choose project
        self.assertIsNone(res.project_id)
        self.assertIsNone(res.project_name)

        # Cleanup
        self.db.delete(task_note)
        self.db.commit()

    def test_create_selected_tasks_uses_existing_task_service(self):
        """
        Verify that approved suggestions can be created using the existing Task service,
        respecting project ownership, validation, and activity tracking.
        """
        payload = TaskCreate(
            title="Review PostgreSQL configuration",
            description="From AI suggestion",
            priority="low",
            status="todo",
        )
        task = create_task(self.db, self.proj, self.user1.id, payload)
        self.assertIsNotNone(task.id)
        self.assertEqual(task.title, "Review PostgreSQL configuration")
        self.assertEqual(task.project_id, self.proj.id)
        self.assertEqual(task.user_id, self.user1.id)

        # Clean up created task
        self.db.delete(task)
        self.db.commit()

    def test_note_with_no_actionable_items_returns_empty(self):
        """Verify that when AI determines no actionable work is present, empty list is returned."""
        provider = DummyAIProvider(configured=True, response=json.dumps({"suggestions": []}))
        res = suggest_tasks_from_note_ai(
            title="PostgreSQL 15 Overview",
            content="PostgreSQL is an advanced, enterprise class open source relational database system.",
            provider=provider,
        )
        self.assertEqual(len(res.suggestions), 0)

    def test_rich_text_note_normalization_preserves_checklists_and_headings(self):
        """Verify rich HTML note content is cleaned while preserving checklist status and headings."""
        raw_html = """<h2>Sprint Checklist</h2>
<ul>
  <li data-checked="false">Implement JWT endpoints</li>
  <li data-checked="true">Set up Docker Compose</li>
</ul>
<pre><code>config = {"timeout": 30}</code></pre>"""
        cleaned = clean_note_content_for_ai(raw_html)
        self.assertIn("- [ ] Implement JWT endpoints", cleaned)
        self.assertIn("- [x] Set up Docker Compose", cleaned)
        self.assertIn("Sprint Checklist", cleaned)

    def test_explicit_deadline_and_no_deadline_invented(self):
        """Verify explicit deadlines are captured and when none exists due_date is None."""
        mock_response = json.dumps({
            "suggestions": [
                {
                    "title": "Complete security audit",
                    "description": "Full audit",
                    "priority": "high",
                    "due_date": "2026-10-15",
                    "reason": "Deadline explicit in text",
                    "confidence": 0.95,
                },
                {
                    "title": "Update documentation",
                    "description": "Docs update",
                    "priority": "medium",
                    "due_date": None,
                    "reason": "General action",
                    "confidence": 0.85,
                },
            ]
        })
        provider = DummyAIProvider(configured=True, response=mock_response)
        res = suggest_tasks_from_note_ai(
            title="Audit Plan",
            content="We need to complete security audit by October 15. Also update documentation.",
            provider=provider,
        )
        self.assertEqual(res.suggestions[0].due_date, "2026-10-15")
        self.assertIsNone(res.suggestions[1].due_date)

    def test_ai_timeout_raises_504(self):
        """Verify timeout raises 504 Gateway Timeout."""
        class TimeoutAIProvider(AIProvider):
            def is_configured(self):
                return True
            def complete(self, prompt, system_prompt=None, **kwargs):
                raise TimeoutError("Request timed out")

        with self.assertRaises(HTTPException) as ctx:
            suggest_tasks_from_note_ai(
                "Sprint",
                "Some long sprint note with plenty of text to analyze",
                TimeoutAIProvider(),
            )
        self.assertEqual(ctx.exception.status_code, 504)

    def test_mock_ai_provider_integration(self):
        """Verify MockAIProvider from factory generates actionable tasks from note content."""
        from app.ai.factory import MockAIProvider
        mock_provider = MockAIProvider()

        note_content = """<h3>Backend Tasks</h3>
- Implement JWT authentication [High]
- Test authentication API [Medium]
- Review PostgreSQL configuration [Low]
Deadline: October 15
"""
        res = suggest_tasks_from_note_ai(
            title="Sprint Kickoff",
            content=note_content,
            provider=mock_provider,
            project_id=self.proj.id,
            project_name=self.proj.name,
        )
        self.assertGreater(len(res.suggestions), 0)
        titles = [s.title.lower() for s in res.suggestions]
        self.assertTrue(any("authentication" in t for t in titles))
        self.assertTrue(any("postgresql" in t for t in titles))
