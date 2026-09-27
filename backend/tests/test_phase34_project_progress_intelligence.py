from datetime import datetime, timedelta, timezone
import unittest

from fastapi import HTTPException
from sqlalchemy import select

from app.ai.base import AIProvider
from app.ai.factory import MockAIProvider, NoopProvider
from app.ai.project_intelligence.schemas import (
    ProjectProgressInsight,
    ProjectProgressIntelligenceResponse,
)
from app.ai.project_intelligence.service import (
    extract_json,
    generate_project_progress_intelligence_ai,
)
from app.db.session import SessionLocal
from app.models.enums import ProjectStatus, TaskPriority, WorkStatus
from app.models.phase import Phase
from app.models.project import Project
from app.models.task import Task
from app.models.user import User
from app.projects.service import get_project_progress_intelligence


class TimeoutAIProvider(AIProvider):
    def is_configured(self) -> bool:
        return True

    def complete(self, prompt: str, system_prompt=None, **kwargs) -> str:
        raise TimeoutError("Model timed out")


class MalformedAIProvider(AIProvider):
    def is_configured(self) -> bool:
        return True

    def complete(self, prompt: str, system_prompt=None, **kwargs) -> str:
        return "This is completely invalid and not JSON"


class TestProjectProgressIntelligence(unittest.TestCase):
    def setUp(self):
        self.db = SessionLocal()

        # User 1
        self.user1 = self.db.execute(
            select(User).where(User.email == "phase34_user1@example.com")
        ).scalar_one_or_none()
        if not self.user1:
            self.user1 = User(
                email="phase34_user1@example.com",
                password_hash="hashed_pw_1",
                name="Phase 34 User One",
            )
            self.db.add(self.user1)
            self.db.commit()
            self.db.refresh(self.user1)

        # User 2 (unauthorized attacker)
        self.user2 = self.db.execute(
            select(User).where(User.email == "phase34_user2@example.com")
        ).scalar_one_or_none()
        if not self.user2:
            self.user2 = User(
                email="phase34_user2@example.com",
                password_hash="hashed_pw_2",
                name="Phase 34 User Two",
            )
            self.db.add(self.user2)
            self.db.commit()
            self.db.refresh(self.user2)

        # Project 1 for User 1
        self.p1 = Project(
            name="Alpha Mobile App",
            user_id=self.user1.id,
            description="Developing the next generation mobile app",
            status=ProjectStatus.ACTIVE,
        )
        self.db.add(self.p1)
        self.db.commit()
        self.db.refresh(self.p1)

        # Empty Project for User 1 (0 tasks)
        self.p_empty = Project(
            name="Empty Project",
            user_id=self.user1.id,
            description="No tasks yet",
            status=ProjectStatus.ACTIVE,
        )
        self.db.add(self.p_empty)
        self.db.commit()
        self.db.refresh(self.p_empty)

        # Project for User 2
        self.p_other = Project(
            name="Secret User2 Project",
            user_id=self.user2.id,
            description="Confidential project",
            status=ProjectStatus.ACTIVE,
        )
        self.db.add(self.p_other)
        self.db.commit()
        self.db.refresh(self.p_other)

    def tearDown(self):
        for p_id in [self.p1.id, self.p_empty.id, self.p_other.id]:
            p = self.db.get(Project, p_id)
            if p:
                self.db.delete(p)
                self.db.commit()
        self.db.close()

    def test_schema_validation_and_normalization(self):
        """Verify schema normalizes types, cleans bullet prefixes, and normalizes severities."""
        item1 = ProjectProgressInsight(
            type="blocker",
            title="• Critical bottleneck detected",
            description="Active task has stalled progress.",
            severity="critical",
        )
        self.assertEqual(item1.type, "bottleneck")
        self.assertEqual(item1.title, "Critical bottleneck detected")
        self.assertEqual(item1.severity, "high")

        item2 = ProjectProgressInsight(
            type="urgent_priority",
            title="- High-priority work unfinished",
            description="Two high-priority tasks are incomplete.",
            severity="moderate",
        )
        self.assertEqual(item2.type, "priority")
        self.assertEqual(item2.title, "High-priority work unfinished")
        self.assertEqual(item2.severity, "medium")

        item3 = ProjectProgressInsight(
            type="due_date",
            title="1. Approaching deadlines",
            description="Task deadline is within 3 days.",
            severity="danger",
        )
        self.assertEqual(item3.type, "deadline")
        self.assertEqual(item3.title, "Approaching deadlines")
        self.assertEqual(item3.severity, "high")

        item4 = ProjectProgressInsight(
            type="task_distribution",
            title="Workload concentrated",
            description="Most incomplete work is in testing.",
            severity="info",
        )
        self.assertEqual(item4.type, "workload")

        item5 = ProjectProgressInsight(
            type="achievement",
            title="Milestone reached",
            description="5 tasks completed.",
            severity="low",
        )
        self.assertEqual(item5.type, "positive")

        resp = ProjectProgressIntelligenceResponse(
            project_summary="The project is progressing steadily.",
            overall_progress=64.4,  # should round to 64
            insights=[item1, item2, item3, item4, item5],
        )
        self.assertEqual(resp.overall_progress, 64)
        self.assertEqual(len(resp.insights), 5)

    def test_empty_project_state(self):
        """A project with 0 tasks returns the clean empty state response without calling AI."""
        resp = get_project_progress_intelligence(
            db=self.db,
            user_id=self.user1.id,
            project_id=self.p_empty.id,
            provider=MockAIProvider(),
        )
        self.assertEqual(resp.overall_progress, 0)
        self.assertEqual(len(resp.insights), 0)
        self.assertIn("No project progress data available yet", resp.project_summary)

    def test_evidence_based_project_intelligence(self):
        """Populate project with tasks, phases, deadlines and verify calculated intelligence."""
        now = datetime.now(timezone.utc)

        # Task 1: Completed (100% progress)
        t1 = Task(
            project_id=self.p1.id,
            user_id=self.user1.id,
            title="Set up database migrations",
            status=WorkStatus.COMPLETED,
            priority=TaskPriority.HIGH,
            progress=100,
        )
        self.db.add(t1)
        self.db.flush()
        ph1 = Phase(task_id=t1.id, title="Schema design", status=WorkStatus.COMPLETED, progress=100)
        ph2 = Phase(task_id=t1.id, title="Run migration", status=WorkStatus.COMPLETED, progress=100)
        self.db.add_all([ph1, ph2])

        # Task 2: In progress, low progress (25% progress - 1 of 4 phases), high priority
        t2 = Task(
            project_id=self.p1.id,
            user_id=self.user1.id,
            title="Implement user authentication API",
            status=WorkStatus.IN_PROGRESS,
            priority=TaskPriority.HIGH,
            progress=25,
            deadline=now + timedelta(days=2),  # approaching deadline
        )
        self.db.add(t2)
        self.db.flush()
        ph2_1 = Phase(task_id=t2.id, title="JWT logic", status=WorkStatus.COMPLETED, progress=100)
        ph2_2 = Phase(task_id=t2.id, title="Password hashing", status=WorkStatus.IN_PROGRESS, progress=0)
        ph2_3 = Phase(task_id=t2.id, title="Refresh token", status=WorkStatus.TODO, progress=0)
        ph2_4 = Phase(task_id=t2.id, title="Login endpoint", status=WorkStatus.TODO, progress=0)
        self.db.add_all([ph2_1, ph2_2, ph2_3, ph2_4])

        # Task 3: In progress, stalled (0% progress - 0 of 2 phases)
        t3 = Task(
            project_id=self.p1.id,
            user_id=self.user1.id,
            title="Push notification service",
            status=WorkStatus.IN_PROGRESS,
            priority=TaskPriority.MEDIUM,
            progress=0,
        )
        self.db.add(t3)
        self.db.flush()
        ph3_1 = Phase(task_id=t3.id, title="Firebase setup", status=WorkStatus.TODO, progress=0)
        ph3_2 = Phase(task_id=t3.id, title="APNS setup", status=WorkStatus.TODO, progress=0)
        self.db.add_all([ph3_1, ph3_2])

        # Task 4: Todo (0% progress)
        t4 = Task(
            project_id=self.p1.id,
            user_id=self.user1.id,
            title="End-to-end integration tests",
            status=WorkStatus.TODO,
            priority=TaskPriority.LOW,
            progress=0,
        )
        self.db.add(t4)
        self.db.commit()

        # Expected overall progress = round((100 + 25 + 0 + 0) / 4) = 31%
        provider = MockAIProvider()
        resp = get_project_progress_intelligence(
            db=self.db,
            user_id=self.user1.id,
            project_id=self.p1.id,
            provider=provider,
        )

        self.assertEqual(resp.overall_progress, 31)
        self.assertGreater(len(resp.insights), 0)

        # Check that expected insight categories are present
        types = [i.type for i in resp.insights]
        self.assertIn("priority", types)
        self.assertIn("deadline", types)
        self.assertIn("positive", types)
        self.assertIn("progress", types)

    def test_unauthorized_user_access_blocked(self):
        """User 2 cannot access Project 1's progress intelligence."""
        with self.assertRaises(HTTPException) as ctx:
            get_project_progress_intelligence(
                db=self.db,
                user_id=self.user2.id,
                project_id=self.p1.id,
                provider=MockAIProvider(),
            )
        self.assertEqual(ctx.exception.status_code, 404)

    def test_nonexistent_project_raises_404(self):
        """Requesting intelligence for a nonexistent project returns 404."""
        with self.assertRaises(HTTPException) as ctx:
            get_project_progress_intelligence(
                db=self.db,
                user_id=self.user1.id,
                project_id=999999,
                provider=MockAIProvider(),
            )
        self.assertEqual(ctx.exception.status_code, 404)

    def test_unconfigured_ai_provider(self):
        """When AI provider is not configured, raises 503."""
        # Add a task so it doesn't short-circuit on empty
        t = Task(
            project_id=self.p1.id,
            user_id=self.user1.id,
            title="Sample task",
            status=WorkStatus.TODO,
        )
        self.db.add(t)
        self.db.commit()

        with self.assertRaises(HTTPException) as ctx:
            get_project_progress_intelligence(
                db=self.db,
                user_id=self.user1.id,
                project_id=self.p1.id,
                provider=NoopProvider(),
            )
        self.assertEqual(ctx.exception.status_code, 503)

    def test_timeout_ai_provider(self):
        """When AI provider times out, raises 504."""
        t = Task(
            project_id=self.p1.id,
            user_id=self.user1.id,
            title="Sample task",
            status=WorkStatus.TODO,
        )
        self.db.add(t)
        self.db.commit()

        with self.assertRaises(HTTPException) as ctx:
            get_project_progress_intelligence(
                db=self.db,
                user_id=self.user1.id,
                project_id=self.p1.id,
                provider=TimeoutAIProvider(),
            )
        self.assertEqual(ctx.exception.status_code, 504)

    def test_malformed_ai_provider(self):
        """When AI provider returns invalid JSON, raises 502."""
        t = Task(
            project_id=self.p1.id,
            user_id=self.user1.id,
            title="Sample task",
            status=WorkStatus.TODO,
        )
        self.db.add(t)
        self.db.commit()

        with self.assertRaises(HTTPException) as ctx:
            get_project_progress_intelligence(
                db=self.db,
                user_id=self.user1.id,
                project_id=self.p1.id,
                provider=MalformedAIProvider(),
            )
        self.assertEqual(ctx.exception.status_code, 502)

    def test_extract_json_helper(self):
        """Verify extract_json handles raw, markdown fenced, and nested JSON."""
        res1 = extract_json('{"key": "value"}')
        self.assertEqual(res1, {"key": "value"})

        res2 = extract_json('```json\n{"key": "markdown"}\n```')
        self.assertEqual(res2, {"key": "markdown"})

        res3 = extract_json('Text before {"key": "nested"} text after')
        self.assertEqual(res3, {"key": "nested"})

    def test_router_endpoint(self):
        """Verify the router endpoint executes successfully and returns ProjectProgressIntelligenceResponse."""
        from app.projects.router import (
            get_project_progress_intelligence_alias,
            get_project_progress_intelligence_endpoint,
        )

        resp = get_project_progress_intelligence_endpoint(
            project_id=self.p_empty.id,
            current_user=self.user1,
            db=self.db,
            ai_provider=MockAIProvider(),
        )
        self.assertIsInstance(resp, ProjectProgressIntelligenceResponse)
        self.assertEqual(resp.overall_progress, 0)

        alias_resp = get_project_progress_intelligence_alias(
            project_id=self.p_empty.id,
            current_user=self.user1,
            db=self.db,
            ai_provider=MockAIProvider(),
        )
        self.assertIsInstance(alias_resp, ProjectProgressIntelligenceResponse)


if __name__ == "__main__":
    unittest.main()

