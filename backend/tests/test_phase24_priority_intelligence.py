import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.ai.base import AIProvider
from app.ai.factory import MockAIProvider
from app.ai.task_priority.prompts import (
    TASK_PRIORITY_SYSTEM_PROMPT,
    build_task_priority_prompt,
)
from app.ai.task_priority.schemas import TaskPriorityAnalysisResponse
from app.ai.task_priority.service import analyze_task_priority_ai
from app.db.session import SessionLocal
from app.models.enums import TaskPriority, WorkStatus
from app.models.project import Project
from app.models.task import Task
from app.models.task_activity import TaskActivity
from app.models.user import User
from app.tasks import service
from app.tasks.router import analyze_task_priority_ai as analyze_priority_endpoint
from app.tasks.schemas import TaskCreate, TaskUpdate


class DummyUnconfiguredProvider(AIProvider):
    def is_configured(self) -> bool:
        return False

    def complete(self, prompt: str, system_prompt=None, **kwargs) -> str:
        return "{}"


class DummyMalformedProvider(AIProvider):
    def is_configured(self) -> bool:
        return True

    def complete(self, prompt: str, system_prompt=None, **kwargs) -> str:
        return "Not valid JSON at all"


class TestPrioritySchemas(unittest.TestCase):
    def test_schema_valid_and_clamping(self):
        res = TaskPriorityAnalysisResponse.model_validate({
            "current_priority": "medium",
            "recommended_priority": "high",
            "confidence": 88,
            "reasoning": "Near deadline and blocks other deliverables.",
            "factors": ["Approaching deadline", "Downstream blocker"],
        })
        self.assertEqual(res.current_priority, "medium")
        self.assertEqual(res.recommended_priority, "high")
        self.assertEqual(res.confidence, 0.88)
        self.assertTrue(res.is_inconsistent)
        self.assertEqual(len(res.factors), 2)

    def test_schema_confidence_percentage_string(self):
        res = TaskPriorityAnalysisResponse.model_validate({
            "current_priority": "low",
            "recommended_priority": "low",
            "confidence": "95%",
            "reasoning": "Scope is minimal and cosmetic.",
            "factors": ["Cosmetic changes only"],
        })
        self.assertEqual(res.confidence, 0.95)
        self.assertFalse(res.is_inconsistent)

    def test_schema_invalid_priority_rejected(self):
        with self.assertRaises(ValidationError):
            TaskPriorityAnalysisResponse.model_validate({
                "current_priority": "medium",
                "recommended_priority": "super-urgent",
                "confidence": 0.9,
                "reasoning": "Invalid priority level",
                "factors": [],
            })


class TestPriorityPrompts(unittest.TestCase):
    def test_prompt_includes_context_and_dependencies(self):
        task = MagicMock(spec=Task)
        task.title = "Fix payment failure affecting checkout"
        task.project_name = "TaskForge E-Commerce"
        task.priority = TaskPriority.MEDIUM
        task.status = WorkStatus.TODO
        task.deadline = datetime.now(timezone.utc) + timedelta(days=1)
        task.description = "Transactions timeout on checkout."
        task.is_blocked = False

        dep = MagicMock()
        dep.depends_on_task.title = "Stripe Gateway Config"
        dep.depends_on_task.status = WorkStatus.COMPLETED
        task.dependencies = [dep]

        dependent = MagicMock()
        dependent.task.title = "Order Confirmation Email"
        task.dependents = [dependent]
        task.phases = []

        prompt = build_task_priority_prompt(task)
        self.assertIn("Task Title: Fix payment failure affecting checkout", prompt)
        self.assertIn("Project: TaskForge E-Commerce", prompt)
        self.assertIn("Current Priority: medium", prompt)
        self.assertIn("Stripe Gateway Config", prompt)
        self.assertIn("Order Confirmation Email", prompt)
        self.assertIn("Deadline:", prompt)


class TestPriorityAIService(unittest.TestCase):
    def test_unconfigured_provider_raises_503(self):
        task = MagicMock(spec=Task)
        task.status = WorkStatus.TODO
        provider = DummyUnconfiguredProvider()
        with self.assertRaises(HTTPException) as ctx:
            analyze_task_priority_ai(task, provider)
        self.assertEqual(ctx.exception.status_code, 503)

    def test_completed_task_raises_400(self):
        task = MagicMock(spec=Task)
        task.status = WorkStatus.COMPLETED
        provider = MockAIProvider()
        with self.assertRaises(HTTPException) as ctx:
            analyze_task_priority_ai(task, provider)
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("Completed tasks do not require priority analysis", ctx.exception.detail)

    def test_malformed_provider_raises_502(self):
        task = MagicMock(spec=Task)
        task.title = "Standard task"
        task.priority = TaskPriority.MEDIUM
        task.status = WorkStatus.TODO
        task.deadline = None
        task.description = "Some description"
        task.dependencies = []
        task.dependents = []
        task.phases = []
        task.is_blocked = False

        provider = DummyMalformedProvider()
        with self.assertRaises(HTTPException) as ctx:
            analyze_task_priority_ai(task, provider)
        self.assertEqual(ctx.exception.status_code, 502)

    def test_mock_provider_payment_failure_analysis(self):
        task = MagicMock(spec=Task)
        task.title = "Fix payment failure affecting checkout"
        task.project_name = "Core App"
        task.priority = TaskPriority.MEDIUM
        task.status = WorkStatus.TODO
        task.deadline = datetime.now(timezone.utc) + timedelta(days=1)
        task.description = "Payment gateway times out during checkout"
        task.dependencies = []
        task.dependents = [MagicMock()]
        task.phases = []
        task.is_blocked = False

        provider = MockAIProvider()
        res = analyze_task_priority_ai(task, provider)
        self.assertEqual(res.current_priority, "medium")
        self.assertIn(res.recommended_priority, ("high", "urgent"))
        self.assertTrue(res.is_inconsistent)
        self.assertGreaterEqual(res.confidence, 0.8)
        self.assertTrue(len(res.factors) > 0)


class TestTaskPriorityDatabaseIntegration(unittest.TestCase):
    def setUp(self):
        self.db: Session = SessionLocal()
        # Find or create a test user
        self.user = self.db.query(User).first()
        if not self.user:
            self.user = User(
                email="test_priority_user@taskforge.ai",
                hashed_password="hashed_pw_test",
                full_name="Priority Test User",
            )
            self.db.add(self.user)
            self.db.commit()
            self.db.refresh(self.user)

        # Create a test project
        self.project = Project(
            name="Priority Intelligence Project",
            user_id=self.user.id,
            description="Testing priority AI features",
        )
        self.db.add(self.project)
        self.db.commit()
        self.db.refresh(self.project)

    def tearDown(self):
        # Clean up test project and associated tasks
        if self.project and self.project.id:
            p = self.db.get(Project, self.project.id)
            if p:
                self.db.delete(p)
                self.db.commit()
        self.db.close()

    def test_priority_analysis_does_not_modify_task_and_approval_works(self):
        # 1. Create task with medium priority
        task_payload = TaskCreate(
            title="Fix payment failure affecting checkout",
            description="Checkout fails on payment webhook",
            priority="medium",
            status="todo",
        )
        task = service.create_task(
            db=self.db, project=self.project, user_id=self.user.id, payload=task_payload
        )
        self.assertEqual(task.priority, TaskPriority.MEDIUM)
        original_updated_at = task.updated_at

        # 2. Run priority AI analysis via service
        provider = MockAIProvider()
        recommendation = service.analyze_task_priority(
            db=self.db, user_id=self.user.id, task_id=task.id, provider=provider
        )

        # Verify recommendation structure
        self.assertEqual(recommendation.current_priority, "medium")
        self.assertIn(recommendation.recommended_priority, ("high", "urgent"))
        self.assertGreaterEqual(recommendation.confidence, 0.0)
        self.assertLessEqual(recommendation.confidence, 1.0)
        self.assertTrue(len(recommendation.reasoning) > 0)
        self.assertTrue(len(recommendation.factors) > 0)

        # Verify task is NOT modified in the database during analysis
        refreshed_task = service.get_owned_task(self.db, self.user.id, task.id)
        self.assertEqual(refreshed_task.priority, TaskPriority.MEDIUM)

        # 3. Test Ownership security check: another user ID cannot analyze task
        with self.assertRaises(HTTPException) as ctx:
            service.analyze_task_priority(
                db=self.db, user_id=self.user.id + 99999, task_id=task.id, provider=provider
            )
        self.assertEqual(ctx.exception.status_code, 404)

        # 4. Apply recommendation via standard update mechanism
        update_payload = TaskUpdate(
            priority=recommendation.recommended_priority,
            source="ai_priority_recommendation",
        )
        updated_task = service.update_task(
            db=self.db, task=refreshed_task, payload=update_payload, user_id=self.user.id
        )

        # Verify task updated
        self.assertEqual(
            updated_task.priority.value, recommendation.recommended_priority
        )

        # Verify activity was recorded
        activities = service.list_task_activities(self.db, self.user.id, task.id)
        priority_act = next(
            (a for a in activities if a.activity_type == "priority_changed"), None
        )
        self.assertIsNotNone(priority_act)
        self.assertIn("Priority changed", priority_act.description)
        self.assertEqual(priority_act.activity_metadata.get("source"), "ai_priority_recommendation")

    def test_completed_task_analysis_rejected(self):
        task_payload = TaskCreate(
            title="Completed Feature",
            priority="low",
            status="completed",
        )
        task = service.create_task(
            db=self.db, project=self.project, user_id=self.user.id, payload=task_payload
        )
        provider = MockAIProvider()
        with self.assertRaises(HTTPException) as ctx:
            service.analyze_task_priority(
                db=self.db, user_id=self.user.id, task_id=task.id, provider=provider
            )
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("Completed tasks do not require priority analysis", ctx.exception.detail)

    def test_endpoint_directly(self):
        task_payload = TaskCreate(
            title="Database migration performance",
            description="Optimize slow query bottlenecks",
            priority="low",
            status="in_progress",
        )
        task = service.create_task(
            db=self.db, project=self.project, user_id=self.user.id, payload=task_payload
        )
        provider = MockAIProvider()
        result = analyze_priority_endpoint(
            task_id=task.id,
            current_user=self.user,
            db=self.db,
            ai_provider=provider,
        )
        self.assertIsInstance(result, TaskPriorityAnalysisResponse)
        self.assertEqual(result.current_priority, "low")
        self.assertIsNotNone(result.recommended_priority)
        self.assertIsNotNone(result.reasoning)
        self.assertTrue(0.0 <= result.confidence <= 1.0)


if __name__ == "__main__":
    unittest.main()
