import json
import unittest
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import select

from app.ai.base import AIProvider
from app.ai.factory import MockAIProvider
from app.ai.project_knowledge.schemas import (
    ProjectAIMessage,
    ProjectAIRequest,
    ProjectAIResponse,
    ProjectAISource,
)
from app.ai.project_knowledge.service import answer_project_question_ai
from app.db.session import SessionLocal
from app.models.enums import ProjectStatus, TaskPriority, WorkStatus
from app.models.note import Note
from app.models.phase import Phase
from app.models.project import Project
from app.models.task import Task
from app.models.user import User
from app.projects.router import ask_project_ai_endpoint


class DummyAIProvider(AIProvider):
    def __init__(self, configured: bool = True, response: str = ""):
        self._configured = configured
        self._response = response
        self.call_count = 0

    def is_configured(self) -> bool:
        return self._configured

    def complete(self, prompt: str, system_prompt: str = None, **kwargs) -> str:
        self.call_count += 1
        if not self._configured:
            raise RuntimeError("Provider not configured")
        return self._response


class TestPhase44ProjectAIKnowledge(unittest.TestCase):
    def setUp(self):
        self.db = SessionLocal()

        # User 1
        self.user1 = self.db.execute(
            select(User).where(User.email == "phase44_user1@example.com")
        ).scalar_one_or_none()
        if not self.user1:
            self.user1 = User(
                email="phase44_user1@example.com",
                password_hash="hashed_pw_1",
                name="Phase 44 User One",
            )
            self.db.add(self.user1)
            self.db.commit()
            self.db.refresh(self.user1)

        # User 2 (for authorization check)
        self.user2 = self.db.execute(
            select(User).where(User.email == "phase44_user2@example.com")
        ).scalar_one_or_none()
        if not self.user2:
            self.user2 = User(
                email="phase44_user2@example.com",
                password_hash="hashed_pw_2",
                name="Phase 44 User Two",
            )
            self.db.add(self.user2)
            self.db.commit()
            self.db.refresh(self.user2)

        # Clean existing test data for these users
        existing_projects = self.db.execute(
            select(Project).where(Project.user_id.in_([self.user1.id, self.user2.id]))
        ).scalars().all()
        for p in existing_projects:
            self.db.delete(p)
        self.db.commit()

        # Create Project for User 1
        self.project = Project(
            user_id=self.user1.id,
            name="E-Commerce Redesign",
            description="Full revamp of customer checkout and authentication services.",
            status=ProjectStatus.ACTIVE,
        )
        self.db.add(self.project)
        self.db.commit()
        self.db.refresh(self.project)

        # Create Tasks for User 1 Project
        self.task1 = Task(
            project_id=self.project.id,
            user_id=self.user1.id,
            title="Implement authentication",
            description="Waiting for API configuration",
            status=WorkStatus.BLOCKED,
            priority=TaskPriority.HIGH,
            deadline=datetime(2026, 10, 15, 12, 0, tzinfo=timezone.utc),
            progress=50,
        )
        self.task2 = Task(
            project_id=self.project.id,
            user_id=self.user1.id,
            title="Deploy service",
            description="Waiting for environment setup",
            status=WorkStatus.BLOCKED,
            priority=TaskPriority.MEDIUM,
            deadline=None,
            progress=0,
        )
        self.task3 = Task(
            project_id=self.project.id,
            user_id=self.user1.id,
            title="Database Schema Migration",
            description="PostgreSQL schema updates for products",
            status=WorkStatus.COMPLETED,
            priority=TaskPriority.URGENT,
            deadline=datetime(2026, 9, 30, 12, 0, tzinfo=timezone.utc),
            progress=100,
        )
        self.db.add_all([self.task1, self.task2, self.task3])
        self.db.commit()
        self.db.refresh(self.task1)
        self.db.refresh(self.task2)
        self.db.refresh(self.task3)

        # Create Phases for Task 1
        self.phase1 = Phase(
            task_id=self.task1.id,
            title="Backend Development",
            description="Implement JWT tokens and FastAPI router",
            status=WorkStatus.IN_PROGRESS,
            progress=50,
            order_index=0,
        )
        self.db.add(self.phase1)

        # Create Notes for User 1 Project
        self.note1 = Note(
            user_id=self.user1.id,
            project_id=self.project.id,
            task_id=self.task1.id,
            title="Authentication Notes",
            content="<h3>Architecture</h3><p>We use JWT and bcrypt.</p>",
        )
        self.db.add(self.note1)
        self.db.commit()
        self.db.refresh(self.phase1)
        self.db.refresh(self.note1)

        # Create Project for User 2 (Secret Project)
        self.project_user2 = Project(
            user_id=self.user2.id,
            name="Confidential Project",
            description="Secret financial platform.",
            status=ProjectStatus.ACTIVE,
        )
        self.db.add(self.project_user2)
        self.db.commit()
        self.db.refresh(self.project_user2)

    def tearDown(self):
        self.db.close()

    def test_ask_blocked_tasks(self):
        """Ask what is blocking the project and verify blocked tasks and descriptions are identified."""
        provider = MockAIProvider()

        res = answer_project_question_ai(
            db=self.db,
            user_id=self.user1.id,
            project_id=self.project.id,
            question="What is currently blocking this project?",
            provider=provider,
        )

        self.assertIn("blocked", res.answer.lower())
        self.assertTrue(len(res.sources) >= 1)
        self.assertTrue(any(s.id == self.task1.id for s in res.sources))

    def test_ask_recommendation_focus(self):
        """Ask what to focus on next; verify separation of Current facts and Suggested focus."""
        provider = MockAIProvider()

        res = answer_project_question_ai(
            db=self.db,
            user_id=self.user1.id,
            project_id=self.project.id,
            question="What should I focus on next?",
            provider=provider,
        )

        self.assertIn("Current facts:", res.answer)
        self.assertIn("Suggested focus:", res.answer)
        self.assertTrue(len(res.sources) >= 1)
        self.assertEqual(res.sources[0].type, "task")

    def test_ask_progress(self):
        """Ask about project progress."""
        provider = MockAIProvider()

        res = answer_project_question_ai(
            db=self.db,
            user_id=self.user1.id,
            project_id=self.project.id,
            question="How much of the project is complete?",
            provider=provider,
        )

        self.assertIn("complete", res.answer.lower())
        self.assertTrue(any(s.id == self.project.id for s in res.sources))

    def test_ask_incomplete_tasks(self):
        """Ask which tasks are incomplete."""
        provider = MockAIProvider()

        res = answer_project_question_ai(
            db=self.db,
            user_id=self.user1.id,
            project_id=self.project.id,
            question="Which tasks are incomplete?",
            provider=provider,
        )

        self.assertIn("Implement authentication", res.answer)
        self.assertTrue(any(s.id == self.task1.id for s in res.sources))

    def test_ask_high_priority_tasks(self):
        """Ask which tasks have high priority."""
        provider = MockAIProvider()

        res = answer_project_question_ai(
            db=self.db,
            user_id=self.user1.id,
            project_id=self.project.id,
            question="Which tasks have high priority?",
            provider=provider,
        )

        self.assertIn("high-priority", res.answer)
        self.assertTrue(any(s.id == self.task1.id for s in res.sources))

    def test_ask_project_notes(self):
        """Ask about decisions recorded in project notes."""
        provider = MockAIProvider()

        res = answer_project_question_ai(
            db=self.db,
            user_id=self.user1.id,
            project_id=self.project.id,
            question="What decisions have been recorded in the project notes?",
            provider=provider,
        )

        self.assertIn("Authentication Notes", res.answer)
        self.assertTrue(any(s.type == "note" and s.id == self.note1.id for s in res.sources))

    def test_ask_phases(self):
        """Ask which phase is currently in progress."""
        provider = MockAIProvider()

        res = answer_project_question_ai(
            db=self.db,
            user_id=self.user1.id,
            project_id=self.project.id,
            question="Which phase is currently in progress?",
            provider=provider,
        )

        self.assertIn("Backend Development", res.answer)
        self.assertTrue(any(s.type == "phase" and s.id == self.phase1.id for s in res.sources))

    def test_ask_deadlines(self):
        """Ask about deadlines coming up."""
        provider = MockAIProvider()

        res = answer_project_question_ai(
            db=self.db,
            user_id=self.user1.id,
            project_id=self.project.id,
            question="What deadlines are coming up?",
            provider=provider,
        )

        self.assertIn("2026-10-15", res.answer)
        self.assertTrue(any(s.id == self.task1.id for s in res.sources))

    def test_ask_missing_information(self):
        """Ask about information not present in the project (e.g. budget)."""
        provider = MockAIProvider()

        res = answer_project_question_ai(
            db=self.db,
            user_id=self.user1.id,
            project_id=self.project.id,
            question="What is the project budget?",
            provider=provider,
        )

        self.assertIn("not contain enough information", res.answer.lower())
        self.assertEqual(res.sources, [])

    def test_follow_up_conversation(self):
        """Test follow-up question passing prior conversation history."""
        provider = MockAIProvider()

        history = [
            ProjectAIMessage(role="user", content="Which tasks are incomplete?"),
            ProjectAIMessage(role="assistant", content="There are 2 incomplete tasks."),
        ]

        res = answer_project_question_ai(
            db=self.db,
            user_id=self.user1.id,
            project_id=self.project.id,
            question="Which of those have high priority?",
            conversation_history=history,
            provider=provider,
        )

        self.assertIn("high-priority", res.answer)
        self.assertTrue(len(res.sources) >= 1)

    def test_unauthorized_project_access(self):
        """Ensure User 1 cannot access or ask questions about User 2's project."""
        provider = MockAIProvider()

        with self.assertRaises(HTTPException) as ctx:
            answer_project_question_ai(
                db=self.db,
                user_id=self.user1.id,
                project_id=self.project_user2.id,
                question="What is the project about?",
                provider=provider,
            )
        self.assertEqual(ctx.exception.status_code, 404)

    def test_question_validation_empty(self):
        """Reject empty and whitespace-only questions."""
        provider = MockAIProvider()

        with self.assertRaises(HTTPException) as ctx:
            answer_project_question_ai(
                db=self.db,
                user_id=self.user1.id,
                project_id=self.project.id,
                question="   ",
                provider=provider,
            )
        self.assertEqual(ctx.exception.status_code, 400)

    def test_unconfigured_ai_provider(self):
        """Return 503 if AI provider is not configured."""
        provider = DummyAIProvider(configured=False)

        with self.assertRaises(HTTPException) as ctx:
            answer_project_question_ai(
                db=self.db,
                user_id=self.user1.id,
                project_id=self.project.id,
                question="What should I focus on next?",
                provider=provider,
            )
        self.assertEqual(ctx.exception.status_code, 503)

    def test_no_data_modification(self):
        """Confirm Project AI never modifies project, task, phase, or note data."""
        orig_p_status = self.project.status
        orig_t_status = self.task1.status
        orig_t_priority = self.task1.priority

        provider = MockAIProvider()
        answer_project_question_ai(
            db=self.db,
            user_id=self.user1.id,
            project_id=self.project.id,
            question="What is currently blocking this project?",
            provider=provider,
        )

        self.db.refresh(self.project)
        self.db.refresh(self.task1)

        self.assertEqual(self.project.status, orig_p_status)
        self.assertEqual(self.task1.status, orig_t_status)
        self.assertEqual(self.task1.priority, orig_t_priority)

    def test_endpoint_integration(self):
        """Test ask_project_ai_endpoint directly with ProjectAIRequest."""
        provider = MockAIProvider()
        req = ProjectAIRequest(question="What is currently blocking this project?")

        res = ask_project_ai_endpoint(
            project_id=self.project.id,
            payload=req,
            current_user=self.user1,
            db=self.db,
            ai_provider=provider,
        )

        self.assertIsInstance(res, ProjectAIResponse)
        self.assertIn("blocked", res.answer.lower())
        self.assertTrue(len(res.sources) >= 1)


if __name__ == "__main__":
    unittest.main()
