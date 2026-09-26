import unittest
from unittest.mock import MagicMock

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.ai.base import AIProvider
from app.ai.factory import MockAIProvider
from app.ai.task_regeneration.prompts import (
    TASK_REGENERATION_SYSTEM_PROMPT,
    build_task_regeneration_prompt,
)
from app.ai.task_regeneration.schemas import (
    TaskRegenerateRequest,
    TaskRegenerateResponse,
)
from app.ai.task_regeneration.service import regenerate_task_ai
from app.db.session import SessionLocal
from app.models.enums import TaskPriority, WorkStatus
from app.models.project import Project
from app.models.task import Task
from app.models.user import User
from app.tasks import service
from app.tasks.router import regenerate_task_endpoint
from app.tasks.schemas import TaskUpdate


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


class DummyTimeoutProvider(AIProvider):
    def is_configured(self) -> bool:
        return True

    def complete(self, prompt: str, system_prompt=None, **kwargs) -> str:
        raise TimeoutError("Simulated timeout error")


class TestTaskRegenerationSchemas(unittest.TestCase):
    def test_schema_valid_and_normalization(self):
        res = TaskRegenerateResponse.model_validate({
            "title": "  \"Title: Fix login authentication failure\" ",
            "description": "  \"Description: Investigate user token creation and redirect logic.\" ",
            "changes": [
                "Clarified problem scope",
                "Added expected outcome",
            ],
        })
        self.assertEqual(res.title, "Fix login authentication failure")
        self.assertEqual(res.description, "Investigate user token creation and redirect logic.")
        self.assertEqual(len(res.changes), 2)
        self.assertEqual(res.changes[0], "Clarified problem scope")

    def test_schema_empty_title_fails(self):
        with self.assertRaises(ValidationError):
            TaskRegenerateResponse.model_validate({
                "title": "   ",
                "description": "Valid description",
            })

    def test_schema_empty_description_fails(self):
        with self.assertRaises(ValidationError):
            TaskRegenerateResponse.model_validate({
                "title": "Valid Title",
                "description": "   ",
            })

    def test_request_schema(self):
        req = TaskRegenerateRequest.model_validate({
            "instruction": "  Make this task suitable for a backend engineer.  "
        })
        self.assertEqual(req.instruction, "Make this task suitable for a backend engineer.")

        empty_req = TaskRegenerateRequest.model_validate({"instruction": "   "})
        self.assertIsNone(empty_req.instruction)


class TestTaskRegenerationPrompts(unittest.TestCase):
    def test_prompt_generation_without_instruction(self):
        proj = Project(id=1, name="Core Platform")
        task = Task(
            id=10,
            title="Fix login",
            description="Login does not work",
            priority=TaskPriority.HIGH,
            status=WorkStatus.TODO,
            project=proj,
        )
        prompt = build_task_regeneration_prompt(task)
        self.assertIn("Task Title: Fix login", prompt)
        self.assertIn("Current Description:\nLogin does not work", prompt)
        self.assertIn("Project: Core Platform", prompt)
        self.assertIn("Priority: high", prompt)
        self.assertIn("rewrite and improve this task", prompt)

    def test_prompt_generation_with_instruction(self):
        proj = Project(id=1, name="Core Platform")
        task = Task(
            id=10,
            title="Update API",
            description="",
            priority=TaskPriority.MEDIUM,
            status=WorkStatus.TODO,
            project=proj,
        )
        prompt = build_task_regeneration_prompt(task, instruction="Focus on REST schema validation")
        self.assertIn("Task Title: Update API", prompt)
        self.assertIn("User Instruction:\nFocus on REST schema validation", prompt)


class TestTaskRegenerationService(unittest.TestCase):
    def test_unconfigured_provider(self):
        task = Task(id=1, title="Sample", project_id=1, user_id=1)
        with self.assertRaises(HTTPException) as ctx:
            regenerate_task_ai(task, DummyUnconfiguredProvider())
        self.assertEqual(ctx.exception.status_code, 503)

    def test_malformed_provider_response(self):
        task = Task(id=1, title="Sample", project_id=1, user_id=1)
        with self.assertRaises(HTTPException) as ctx:
            regenerate_task_ai(task, DummyMalformedProvider())
        self.assertEqual(ctx.exception.status_code, 502)

    def test_timeout_provider(self):
        task = Task(id=1, title="Sample", project_id=1, user_id=1)
        with self.assertRaises(HTTPException) as ctx:
            regenerate_task_ai(task, DummyTimeoutProvider())
        self.assertEqual(ctx.exception.status_code, 504)

    def test_mock_provider_regeneration(self):
        provider = MockAIProvider()
        task = Task(
            id=1,
            title="Fix login",
            description="Login doesn't work.",
            priority=TaskPriority.HIGH,
            status=WorkStatus.TODO,
        )
        res = regenerate_task_ai(task, provider)
        self.assertIsInstance(res, TaskRegenerateResponse)
        self.assertIn("authentication", res.title.lower())
        self.assertTrue(len(res.description) > len(task.description))
        self.assertTrue(len(res.changes) > 0)

    def test_mock_provider_with_instruction(self):
        provider = MockAIProvider()
        task = Task(
            id=1,
            title="Setup database",
            description="Init db",
            priority=TaskPriority.MEDIUM,
            status=WorkStatus.TODO,
        )
        res = regenerate_task_ai(task, provider, instruction="Use PostgreSQL with Alembic migrations")
        self.assertIsInstance(res, TaskRegenerateResponse)
        self.assertIn("PostgreSQL with Alembic migrations", res.description)


class TestTaskRegenerationEndpointsIntegration(unittest.TestCase):
    def setUp(self):
        self.db = MagicMock(spec=Session)
        self.user = User(id=42, email="user@taskforge.ai")
        self.other_user = User(id=99, email="other@taskforge.ai")

    def test_endpoint_task_ownership_security(self):
        self.db.execute.return_value.scalar_one_or_none.return_value = None
        with self.assertRaises(HTTPException) as ctx:
            regenerate_task_endpoint(
                task_id=999,
                payload=TaskRegenerateRequest(instruction="Make clearer"),
                current_user=self.other_user,
                db=self.db,
                ai_provider=MockAIProvider(),
            )
        self.assertEqual(ctx.exception.status_code, 404)


class TestTaskRegenerationDatabaseIntegration(unittest.TestCase):
    def setUp(self):
        self.db: Session = SessionLocal()
        self.user = self.db.query(User).first()
        if not self.user:
            self.user = User(
                email="test_regen_user@taskforge.ai",
                hashed_password="hashed_pw_test",
                full_name="Regen Test User",
            )
            self.db.add(self.user)
            self.db.commit()
            self.db.refresh(self.user)

        self.project = Project(
            name="Regeneration Test Project",
            user_id=self.user.id,
            description="Testing AI task regeneration flow",
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

    def test_full_regeneration_and_apply_flow(self):
        # 1. Create a task with vague title and minimal description
        task = Task(
            project_id=self.project.id,
            user_id=self.user.id,
            title="Fix login",
            description="Login doesn't work.",
            status=WorkStatus.TODO,
            priority=TaskPriority.HIGH,
        )
        self.db.add(task)
        self.db.commit()
        self.db.refresh(task)

        original_id = task.id
        original_title = task.title
        original_desc = task.description
        original_status = task.status
        original_priority = task.priority

        # 2. Call regeneration endpoint (should NOT modify DB)
        provider = MockAIProvider()
        proposal = regenerate_task_endpoint(
            task_id=task.id,
            payload=TaskRegenerateRequest(instruction="Add acceptance criteria"),
            current_user=self.user,
            db=self.db,
            ai_provider=provider,
        )

        self.assertIsInstance(proposal, TaskRegenerateResponse)
        self.assertNotEqual(proposal.title, original_title)
        self.assertTrue(len(proposal.description) > len(original_desc))
        self.assertTrue(len(proposal.changes) > 0)

        # 3. VERIFY: The database task remains completely unchanged!
        db_task_check = self.db.get(Task, original_id)
        self.assertEqual(db_task_check.title, original_title)
        self.assertEqual(db_task_check.description, original_desc)

        # 4. User approves and applies changes via existing update mechanism
        update_payload = TaskUpdate(
            title=proposal.title,
            description=proposal.description,
        )
        updated_task = service.update_task(
            db=self.db,
            task=db_task_check,
            payload=update_payload,
            user_id=self.user.id,
        )

        # 5. VERIFY: Task title & description updated, other fields preserved
        self.assertEqual(updated_task.title, proposal.title)
        self.assertEqual(updated_task.description, proposal.description)
        self.assertEqual(updated_task.status, original_status)
        self.assertEqual(updated_task.priority, original_priority)
        self.assertEqual(updated_task.project_id, self.project.id)

        # 6. VERIFY: Task Activity System recorded the change
        activities = service.list_task_activities(self.db, self.user.id, updated_task.id)
        self.assertTrue(len(activities) > 0)
        title_activity = next((a for a in activities if "Title changed" in a.description), None)
        self.assertIsNotNone(title_activity)
        self.assertEqual(title_activity.activity_metadata["old_title"], original_title)
        self.assertEqual(title_activity.activity_metadata["new_title"], proposal.title)


if __name__ == "__main__":
    unittest.main()
