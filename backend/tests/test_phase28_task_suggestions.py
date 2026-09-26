import unittest
from datetime import datetime, timezone
from unittest.mock import MagicMock

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.ai.base import AIProvider
from app.ai.factory import MockAIProvider
from app.ai.task_suggestions.prompts import (
    TASK_SUGGESTIONS_SYSTEM_PROMPT,
    build_project_task_suggestions_prompt,
    build_task_level_suggestions_prompt,
)
from app.ai.task_suggestions.schemas import (
    ApplyTaskSuggestionsRequest,
    TaskSuggestionItem,
    TaskSuggestionsResponse,
)
from app.ai.task_suggestions.service import (
    filter_duplicate_suggestions,
    generate_project_task_suggestions,
    generate_task_related_suggestions,
    normalize_title,
)
from app.db.session import SessionLocal
from app.models.enums import TaskPriority, WorkStatus
from app.models.project import Project
from app.models.task import Task
from app.models.user import User
from app.tasks import service
from app.tasks.router import (
    apply_project_task_suggestions_endpoint,
    apply_task_related_suggestions_endpoint,
    get_project_task_suggestions_endpoint,
    get_task_related_suggestions_endpoint,
)


class DummyUnconfiguredProvider(AIProvider):
    def is_configured(self) -> bool:
        return False

    def complete(self, prompt: str, system_prompt=None, **kwargs) -> str:
        return "{}"


class DummyMalformedProvider(AIProvider):
    def is_configured(self) -> bool:
        return True

    def complete(self, prompt: str, system_prompt=None, **kwargs) -> str:
        return "This is definitely not JSON!"


class DummyTimeoutProvider(AIProvider):
    def is_configured(self) -> bool:
        return True

    def complete(self, prompt: str, system_prompt=None, **kwargs) -> str:
        raise TimeoutError("Simulated timeout error")


class TestTaskSuggestionsSchemas(unittest.TestCase):
    def test_schema_valid_and_normalization(self):
        item = TaskSuggestionItem.model_validate({
            "title": " 1. Add API Integration Tests ",
            "description": "  Test critical endpoints.  ",
            "reason": "  Coverage is needed. ",
            "priority": "HIGH",
        })
        self.assertEqual(item.title, "Add API Integration Tests")
        self.assertEqual(item.description, "Test critical endpoints.")
        self.assertEqual(item.reason, "Coverage is needed.")
        self.assertEqual(item.priority, "high")

    def test_schema_priority_fallback(self):
        # Invalid priority falls back to medium
        item = TaskSuggestionItem.model_validate({
            "title": "- Implement Webhook Listener",
            "priority": "super_urgent_invalid",
        })
        self.assertEqual(item.title, "Implement Webhook Listener")
        self.assertEqual(item.priority, "medium")

    def test_schema_title_bullet_stripping(self):
        item = TaskSuggestionItem.model_validate({
            "title": "* Setup Monitoring Alerts",
        })
        self.assertEqual(item.title, "Setup Monitoring Alerts")

    def test_schema_empty_title_fails(self):
        with self.assertRaises(ValidationError):
            TaskSuggestionItem.model_validate({"title": "   "})

    def test_apply_request_validation(self):
        # Empty suggestions list should fail validation
        with self.assertRaises(ValidationError):
            ApplyTaskSuggestionsRequest.model_validate({"suggestions": []})

        req = ApplyTaskSuggestionsRequest.model_validate({
            "suggestions": [
                {"title": "Valid Task", "priority": "low"}
            ]
        })
        self.assertEqual(len(req.suggestions), 1)


class TestDuplicateDetection(unittest.TestCase):
    def test_normalize_title(self):
        self.assertEqual(
            normalize_title("  1. Add API Integration Tests! "),
            "add api integration tests",
        )
        self.assertEqual(
            normalize_title("add   API integration   tests"),
            "add api integration tests",
        )
        self.assertEqual(
            normalize_title("- Email Verification (New)"),
            "email verification new",
        )

    def test_filter_duplicate_suggestions(self):
        existing = [
            Task(id=1, title="User Authentication", project_id=1, user_id=1),
            Task(id=2, title="Payment Integration", project_id=1, user_id=1),
        ]
        suggs = [
            TaskSuggestionItem(title="User Authentication", description="Duplicate of 1"),
            TaskSuggestionItem(title="user authentication", description="Case duplicate of 1"),
            TaskSuggestionItem(title="Add Email Verification", description="Unique item"),
            TaskSuggestionItem(title="add email verification", description="Duplicate within batch"),
            TaskSuggestionItem(title="Payment Integration!", description="Punctuation duplicate of 2"),
            TaskSuggestionItem(title="Setup CI/CD", description="Another unique item"),
        ]

        filtered = filter_duplicate_suggestions(suggs, existing)
        self.assertEqual(len(filtered), 2)
        self.assertEqual(filtered[0].title, "Add Email Verification")
        self.assertEqual(filtered[1].title, "Setup CI/CD")


class TestTaskSuggestionsPrompts(unittest.TestCase):
    def test_project_prompt_generation(self):
        proj = Project(
            id=10,
            name="E-Commerce Store",
            description="Online store with cart and payments.",
            status="active",
        )
        tasks = [
            Task(
                id=1,
                title="User Auth",
                description="Login and registration",
                priority=TaskPriority.HIGH,
                status=WorkStatus.COMPLETED,
            )
        ]
        prompt = build_project_task_suggestions_prompt(proj, tasks)
        self.assertIn("Project: E-Commerce Store", prompt)
        self.assertIn("Online store with cart and payments", prompt)
        self.assertIn("User Auth", prompt)

    def test_task_level_prompt_generation(self):
        proj = Project(id=10, name="E-Commerce Store")
        target_task = Task(
            id=1,
            title="Payment Gateway Integration",
            description="Stripe integration",
            priority=TaskPriority.HIGH,
            status=WorkStatus.IN_PROGRESS,
            project=proj,
        )
        other_tasks = [
            Task(id=2, title="User Auth", status=WorkStatus.COMPLETED, project=proj),
            Task(id=3, title="Product Catalog", status=WorkStatus.TODO, project=proj),
        ]
        prompt = build_task_level_suggestions_prompt(target_task, other_tasks)
        self.assertIn("Task Title: Payment Gateway Integration", prompt)
        self.assertIn("Project: E-Commerce Store", prompt)
        self.assertIn("User Auth", prompt)


class TestTaskSuggestionsService(unittest.TestCase):
    def test_unconfigured_provider_error(self):
        proj = Project(id=1, name="Test Project")
        with self.assertRaises(HTTPException) as ctx:
            generate_project_task_suggestions(proj, [], DummyUnconfiguredProvider())
        self.assertEqual(ctx.exception.status_code, 503)

    def test_malformed_provider_error(self):
        proj = Project(id=1, name="Test Project")
        with self.assertRaises(HTTPException) as ctx:
            generate_project_task_suggestions(proj, [], DummyMalformedProvider())
        self.assertEqual(ctx.exception.status_code, 502)

    def test_timeout_provider_error(self):
        proj = Project(id=1, name="Test Project")
        with self.assertRaises(HTTPException) as ctx:
            generate_project_task_suggestions(proj, [], DummyTimeoutProvider())
        self.assertEqual(ctx.exception.status_code, 504)

    def test_mock_provider_suggestions_and_duplicate_filtering(self):
        mock_ai = MockAIProvider()
        proj = Project(id=1, name="E-commerce Application", description="Store app")
        # Pre-existing tasks including "User Authentication" and "Add API Integration Tests"
        existing = [
            Task(id=1, title="User Authentication", project_id=1, user_id=1, priority=TaskPriority.MEDIUM, status=WorkStatus.COMPLETED),
            Task(id=2, title="Add API Integration Tests", project_id=1, user_id=1, priority=TaskPriority.MEDIUM, status=WorkStatus.TODO),
        ]

        res = generate_project_task_suggestions(proj, existing, mock_ai)
        self.assertIsInstance(res, TaskSuggestionsResponse)
        # "Add API Integration Tests" should have been filtered out!
        titles = [s.title for s in res.suggestions]
        self.assertNotIn("Add API Integration Tests", titles)
        # Other valid suggestions should be present
        self.assertTrue(any("Email Verification" in t or "Order" in t for t in titles))

    def test_mock_provider_empty_suggestions(self):
        mock_ai = MockAIProvider()
        proj = Project(id=1, name="Project [FORCE_EMPTY_SUGGESTIONS]", description="Testing empty")
        res = generate_project_task_suggestions(proj, [], mock_ai)
        self.assertEqual(len(res.suggestions), 0)


class TestEndpointsIntegration(unittest.TestCase):
    def setUp(self):
        self.db = MagicMock(spec=Session)
        self.user = User(id=42, email="user@taskforge.ai")
        self.other_user = User(id=99, email="other@taskforge.ai")
        self.project = Project(id=101, user_id=42, name="Test App", description="Testing")
        self.task = Task(id=202, project_id=101, user_id=42, title="Base Task", priority=TaskPriority.MEDIUM, status=WorkStatus.TODO)
        self.task.project = self.project

    def test_endpoint_project_ownership_security(self):
        self.db.execute.return_value.scalar_one_or_none.return_value = None
        with self.assertRaises(HTTPException) as ctx:
            get_project_task_suggestions_endpoint(
                project_id=999,
                current_user=self.other_user,
                db=self.db,
                ai_provider=MockAIProvider(),
            )
        self.assertEqual(ctx.exception.status_code, 404)

    def test_endpoint_task_ownership_security(self):
        self.db.execute.return_value.scalar_one_or_none.return_value = None
        with self.assertRaises(HTTPException) as ctx:
            get_task_related_suggestions_endpoint(
                task_id=999,
                current_user=self.other_user,
                db=self.db,
                ai_provider=MockAIProvider(),
            )
        self.assertEqual(ctx.exception.status_code, 404)


class TestTaskSuggestionsDatabaseIntegration(unittest.TestCase):
    def setUp(self):
        self.db: Session = SessionLocal()
        self.user = self.db.query(User).first()
        if not self.user:
            self.user = User(
                email="test_suggestions_user@taskforge.ai",
                hashed_password="hashed_pw_test",
                full_name="Suggestions Test User",
            )
            self.db.add(self.user)
            self.db.commit()
            self.db.refresh(self.user)

        self.project = Project(
            name="E-Commerce AI Suggestions Project",
            user_id=self.user.id,
            description="Store project to test suggestions",
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

    def test_full_project_suggestions_and_apply_flow(self):
        # 1. Initially create 1 task
        initial_task = Task(
            project_id=self.project.id,
            user_id=self.user.id,
            title="User Authentication",
            description="Login and registration",
            status=WorkStatus.COMPLETED,
            priority=TaskPriority.HIGH,
        )
        self.db.add(initial_task)
        self.db.commit()

        # 2. Get suggestions using endpoint
        provider = MockAIProvider()
        suggestions_res = get_project_task_suggestions_endpoint(
            project_id=self.project.id,
            current_user=self.user,
            db=self.db,
            ai_provider=provider,
        )
        self.assertIsInstance(suggestions_res, TaskSuggestionsResponse)
        self.assertTrue(len(suggestions_res.suggestions) > 0)

        # Verify duplicate prevention: User Authentication should NOT be suggested
        titles = [s.title for s in suggestions_res.suggestions]
        self.assertNotIn("User Authentication", titles)

        # 3. Apply selected suggestions
        selected = suggestions_res.suggestions[:2]
        apply_payload = ApplyTaskSuggestionsRequest(suggestions=selected)
        created_tasks = apply_project_task_suggestions_endpoint(
            project_id=self.project.id,
            payload=apply_payload,
            current_user=self.user,
            db=self.db,
        )

        self.assertEqual(len(created_tasks), len(selected))
        for ct in created_tasks:
            self.assertEqual(ct.project_id, self.project.id)
            self.assertIn(ct.status, ["todo"])
            self.assertIn(ct.priority, ["low", "medium", "high", "urgent"])

        # 4. Verify created task activities were recorded
        db_tasks = service.list_tasks(self.db, self.project.id)
        self.assertEqual(len(db_tasks), 1 + len(selected))

        # Check activities for newly created task
        first_created = created_tasks[0]
        activities = service.list_task_activities(self.db, self.user.id, first_created.id)
        self.assertTrue(len(activities) > 0)
        self.assertEqual(activities[0].activity_type, "created")
        self.assertIn("Task created from AI suggestion", activities[0].description)

        # 5. Prevent duplicates on repeated apply
        # Applying the exact same suggestions again should create 0 duplicate tasks!
        second_apply = apply_project_task_suggestions_endpoint(
            project_id=self.project.id,
            payload=apply_payload,
            current_user=self.user,
            db=self.db,
        )
        self.assertEqual(len(second_apply), 0)
        db_tasks_after = service.list_tasks(self.db, self.project.id)
        self.assertEqual(len(db_tasks_after), len(db_tasks))


if __name__ == "__main__":
    unittest.main()

