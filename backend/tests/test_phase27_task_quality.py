import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.ai.base import AIProvider
from app.ai.factory import MockAIProvider
from app.ai.task_quality.prompts import (
    TASK_QUALITY_SYSTEM_PROMPT,
    build_task_quality_prompt,
)
from app.ai.task_quality.schemas import (
    TaskQualityDimension,
    TaskQualityIssue,
    TaskQualityResponse,
    TaskQualitySuggestion,
)
from app.ai.task_quality.service import analyze_task_quality_ai
from app.db.session import SessionLocal
from app.models.enums import TaskPriority, WorkStatus
from app.models.project import Project
from app.models.task import Task
from app.models.user import User
from app.tasks import service
from app.tasks.router import analyze_task_quality_endpoint
from app.tasks.schemas import TaskCreate


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


class TestTaskQualitySchemas(unittest.TestCase):
    def test_schema_valid_and_clamping(self):
        res = TaskQualityResponse.model_validate({
            "overall_score": 72,
            "summary": "Good foundation, but expected outcome could be more specific.",
            "dimensions": [
                {"name": "clarity", "score": 80, "explanation": "Clear objective."},
                {"name": "specificity", "score": 60, "explanation": "Lacks specific expected result."},
                {"name": "actionability", "score": 80, "explanation": "Can be started easily."},
                {"name": "completeness", "score": 70, "explanation": "Basic scope outlined."},
                {"name": "context", "score": 75, "explanation": "Context provided."},
            ],
            "issues": [
                {
                    "title": "Expected result is unclear",
                    "description": "The task does not explain what success looks like.",
                    "severity": "medium",
                }
            ],
            "suggestions": [
                {
                    "title": "Define the expected result",
                    "description": "Describe what should be different after the task is completed.",
                }
            ],
        })
        self.assertEqual(res.overall_score, 72)
        self.assertEqual(len(res.dimensions), 5)
        self.assertEqual(len(res.issues), 1)
        self.assertEqual(len(res.suggestions), 1)
        self.assertEqual(res.issues[0].severity, "medium")

    def test_score_clamping_and_normalization(self):
        dim = TaskQualityDimension.model_validate({
            "name": "Clarity ",
            "score": "85%",
            "explanation": "Clear",
        })
        self.assertEqual(dim.name, "clarity")
        self.assertEqual(dim.score, 85)

        # Clamping out-of-range
        dim_high = TaskQualityDimension.model_validate({
            "name": "specificity",
            "score": 150,
            "explanation": "Over 100",
        })
        self.assertEqual(dim_high.score, 100)

        dim_low = TaskQualityDimension.model_validate({
            "name": "specificity",
            "score": -20,
            "explanation": "Negative",
        })
        self.assertEqual(dim_low.score, 0)

    def test_severity_normalization(self):
        issue = TaskQualityIssue.model_validate({
            "title": "Missing acceptance criteria",
            "description": "No criteria defined",
            "severity": "HIGH",
        })
        self.assertEqual(issue.severity, "high")

        # Unknown severity defaults to medium
        issue_unknown = TaskQualityIssue.model_validate({
            "title": "Minor warning",
            "description": "Details",
            "severity": "unknown_value",
        })
        self.assertEqual(issue_unknown.severity, "medium")


class TestTaskQualityPrompts(unittest.TestCase):
    def test_prompt_includes_all_context(self):
        task = MagicMock(spec=Task)
        task.title = "Implement user avatar upload"
        task.project_name = "Core App"
        task.priority = TaskPriority.HIGH
        task.status = WorkStatus.IN_PROGRESS
        task.deadline = datetime.now(timezone.utc) + timedelta(days=2)
        task.description = "Allow users to upload PNG or JPG avatars up to 5MB."
        task.phases = [MagicMock(title="Backend S3 API"), MagicMock(title="Frontend Avatar Picker")]
        task.dependencies = [MagicMock()]

        prompt = build_task_quality_prompt(task)
        self.assertIn("Task Title: Implement user avatar upload", prompt)
        self.assertIn("Project: Core App", prompt)
        self.assertIn("Priority: high", prompt)
        self.assertIn("Status: in_progress", prompt)
        self.assertIn("Backend S3 API", prompt)
        self.assertIn("Frontend Avatar Picker", prompt)
        self.assertIn("Dependencies:", prompt)


class TestTaskQualityAIService(unittest.TestCase):
    def test_unconfigured_provider_raises_503(self):
        task = MagicMock(spec=Task)
        provider = DummyUnconfiguredProvider()
        with self.assertRaises(HTTPException) as ctx:
            analyze_task_quality_ai(task, provider)
        self.assertEqual(ctx.exception.status_code, 503)

    def test_malformed_provider_raises_502(self):
        task = MagicMock(spec=Task)
        task.title = "Sample"
        task.description = "Sample desc"
        task.priority = TaskPriority.MEDIUM
        task.status = WorkStatus.TODO
        task.deadline = None
        task.phases = []
        task.dependencies = []

        provider = DummyMalformedProvider()
        with self.assertRaises(HTTPException) as ctx:
            analyze_task_quality_ai(task, provider)
        self.assertEqual(ctx.exception.status_code, 502)

    def test_mock_provider_vague_task_evaluation(self):
        task = MagicMock(spec=Task)
        task.title = "Fix website"
        task.project_name = "Web Portal"
        task.priority = TaskPriority.MEDIUM
        task.status = WorkStatus.TODO
        task.deadline = None
        task.description = ""
        task.phases = []
        task.dependencies = []

        provider = MockAIProvider()
        res = analyze_task_quality_ai(task, provider)
        self.assertIsInstance(res, TaskQualityResponse)
        self.assertLessEqual(res.overall_score, 60)
        self.assertTrue(len(res.issues) > 0)
        self.assertTrue(len(res.suggestions) > 0)
        self.assertEqual(len(res.dimensions), 5)

    def test_mock_provider_detailed_task_evaluation(self):
        task = MagicMock(spec=Task)
        task.title = "Build rate limiting middleware for FastAPI authentication endpoints"
        task.project_name = "API Security"
        task.priority = TaskPriority.HIGH
        task.status = WorkStatus.TODO
        task.deadline = datetime.now(timezone.utc) + timedelta(days=3)
        task.description = "Implement a Redis-backed sliding window rate limiter allowing max 5 login requests per minute per IP address, returning HTTP 429."
        task.phases = []
        task.dependencies = []

        provider = MockAIProvider()
        res = analyze_task_quality_ai(task, provider)
        self.assertIsInstance(res, TaskQualityResponse)
        self.assertGreaterEqual(res.overall_score, 80)
        self.assertEqual(len(res.dimensions), 5)


class TestTaskQualityDatabaseIntegration(unittest.TestCase):
    def setUp(self):
        self.db: Session = SessionLocal()
        self.user = self.db.query(User).first()
        if not self.user:
            self.user = User(
                email="test_quality_user@taskforge.ai",
                hashed_password="hashed_pw_test",
                full_name="Quality Test User",
            )
            self.db.add(self.user)
            self.db.commit()
            self.db.refresh(self.user)

        self.project = Project(
            name="Quality Test Project",
            user_id=self.user.id,
            description="Testing quality scoring",
        )
        self.db.add(self.project)
        self.db.commit()
        self.db.refresh(self.project)

    def tearDown(self):
        if self.project and self.project.id:
            p = self.db.get(Project, self.project.id)
            if p:
                self.db.delete(p)
                self.db.commit()
        self.db.close()

    def test_quality_analysis_does_not_modify_task(self):
        # 1. Create a task
        task_payload = TaskCreate(
            title="Fix website",
            description="",
            priority="medium",
            status="todo",
        )
        task = service.create_task(
            db=self.db, project=self.project, user_id=self.user.id, payload=task_payload
        )
        original_title = task.title
        original_desc = task.description
        original_priority = task.priority
        original_updated_at = task.updated_at

        # 2. Run quality analysis
        provider = MockAIProvider()
        result = service.analyze_task_quality(
            db=self.db, user_id=self.user.id, task_id=task.id, provider=provider
        )

        self.assertIsInstance(result, TaskQualityResponse)
        self.assertTrue(0 <= result.overall_score <= 100)
        self.assertTrue(len(result.dimensions) > 0)
        self.assertTrue(len(result.issues) > 0)
        self.assertTrue(len(result.suggestions) > 0)

        # 3. Verify task was NOT modified in the database
        refreshed_task = service.get_owned_task(self.db, self.user.id, task.id)
        self.assertEqual(refreshed_task.title, original_title)
        self.assertEqual(refreshed_task.description, original_desc)
        self.assertEqual(refreshed_task.priority, original_priority)
        self.assertEqual(refreshed_task.updated_at, original_updated_at)

    def test_ownership_check(self):
        task_payload = TaskCreate(
            title="Private Task",
            description="Confidential task details",
            priority="low",
            status="todo",
        )
        task = service.create_task(
            db=self.db, project=self.project, user_id=self.user.id, payload=task_payload
        )
        provider = MockAIProvider()

        # Another user cannot analyze the task
        with self.assertRaises(HTTPException) as ctx:
            service.analyze_task_quality(
                db=self.db, user_id=self.user.id + 99999, task_id=task.id, provider=provider
            )
        self.assertEqual(ctx.exception.status_code, 404)

    def test_endpoint_directly(self):
        task_payload = TaskCreate(
            title="Refactor database indexes",
            description="Add compound indexes for user activity queries to reduce query latency below 50ms.",
            priority="medium",
            status="todo",
        )
        task = service.create_task(
            db=self.db, project=self.project, user_id=self.user.id, payload=task_payload
        )
        provider = MockAIProvider()
        result = analyze_task_quality_endpoint(
            task_id=task.id,
            current_user=self.user,
            db=self.db,
            ai_provider=provider,
        )
        self.assertIsInstance(result, TaskQualityResponse)
        self.assertGreaterEqual(result.overall_score, 0)
        self.assertLessEqual(result.overall_score, 100)
        self.assertIsNotNone(result.summary)


if __name__ == "__main__":
    unittest.main()
