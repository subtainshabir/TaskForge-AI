from datetime import datetime, timedelta, timezone
import unittest

from fastapi import HTTPException
from sqlalchemy import select

from app.ai.base import AIProvider
from app.ai.factory import MockAIProvider, NoopProvider
from app.ai.progress_insights.schemas import ProgressInsightItem, ProgressInsightsResponse
from app.ai.progress_insights.service import extract_json, generate_progress_insights_ai
from app.analytics.service import get_progress_insights
from app.db.session import SessionLocal
from app.models.enums import TaskPriority, WorkStatus
from app.models.phase import Phase
from app.models.project import Project
from app.models.task import Task
from app.models.user import User


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


class TestAIProgressInsights(unittest.TestCase):
    def setUp(self):
        self.db = SessionLocal()

        # User 1
        self.user1 = self.db.execute(
            select(User).where(User.email == "phase33_user1@example.com")
        ).scalar_one_or_none()
        if not self.user1:
            self.user1 = User(
                email="phase33_user1@example.com",
                password_hash="hashed_pw_1",
                name="Phase 33 User One",
            )
            self.db.add(self.user1)
            self.db.commit()
            self.db.refresh(self.user1)

        # User 2
        self.user2 = self.db.execute(
            select(User).where(User.email == "phase33_user2@example.com")
        ).scalar_one_or_none()
        if not self.user2:
            self.user2 = User(
                email="phase33_user2@example.com",
                password_hash="hashed_pw_2",
                name="Phase 33 User Two",
            )
            self.db.add(self.user2)
            self.db.commit()
            self.db.refresh(self.user2)

        # Projects for User 1
        self.p1 = Project(name="Project Alpha", user_id=self.user1.id, description="Alpha project")
        self.db.add(self.p1)
        self.db.commit()
        self.db.refresh(self.p1)

        # Project for User 2
        self.p_other = Project(name="Secret Project", user_id=self.user2.id)
        self.db.add(self.p_other)
        self.db.commit()
        self.db.refresh(self.p_other)

    def tearDown(self):
        for p_id in [self.p1.id, self.p_other.id]:
            p = self.db.get(Project, p_id)
            if p:
                self.db.delete(p)
                self.db.commit()
        self.db.close()

    def test_schema_validation_and_normalization(self):
        item = ProgressInsightItem(
            type="blocker",
            title="• Critical bottleneck detected",
            description="Four active tasks have stalled progress.",
            severity="critical",
        )
        self.assertEqual(item.type, "bottleneck")
        self.assertEqual(item.title, "Critical bottleneck detected")
        self.assertEqual(item.severity, "high")

        item2 = ProgressInsightItem(
            type="stuck",
            title="Tasks stalled",
            description="No movement on active phases.",
            severity="moderate",
        )
        self.assertEqual(item2.type, "stalled")
        self.assertEqual(item2.severity, "medium")

        item3 = ProgressInsightItem(
            type="achievement",
            title="Milestone reached",
            description="All phases completed.",
            severity="info",
        )
        self.assertEqual(item3.type, "positive")

        resp = ProgressInsightsResponse(
            summary="Workspace progress is steady.",
            insights=[item, item2, item3],
        )
        self.assertEqual(len(resp.insights), 3)

    def test_empty_workspace_returns_empty_insights_without_ai_call(self):
        # User 1 has no tasks in Project Alpha
        mock_provider = MockAIProvider()
        result = get_progress_insights(self.db, self.user1.id, provider=mock_provider)
        self.assertEqual(result.summary, "Not enough task data for meaningful AI insights yet.")
        self.assertEqual(len(result.insights), 0)

    def test_unconfigured_ai_provider_raises_503(self):
        # Create a task for user 1
        t = Task(project_id=self.p1.id, user_id=self.user1.id, title="Task 1", status=WorkStatus.TODO)
        self.db.add(t)
        self.db.commit()

        noop = NoopProvider()
        with self.assertRaises(HTTPException) as cm:
            get_progress_insights(self.db, self.user1.id, provider=noop)
        self.assertEqual(cm.exception.status_code, 503)

    def test_malformed_ai_provider_raises_502(self):
        t = Task(project_id=self.p1.id, user_id=self.user1.id, title="Task 1", status=WorkStatus.TODO)
        self.db.add(t)
        self.db.commit()

        malformed = MalformedAIProvider()
        with self.assertRaises(HTTPException) as cm:
            get_progress_insights(self.db, self.user1.id, provider=malformed)
        self.assertEqual(cm.exception.status_code, 502)

    def test_timeout_ai_provider_raises_504(self):
        t = Task(project_id=self.p1.id, user_id=self.user1.id, title="Task 1", status=WorkStatus.TODO)
        self.db.add(t)
        self.db.commit()

        timeout_prov = TimeoutAIProvider()
        with self.assertRaises(HTTPException) as cm:
            get_progress_insights(self.db, self.user1.id, provider=timeout_prov)
        self.assertEqual(cm.exception.status_code, 504)

    def test_mock_provider_generates_evidence_based_insights(self):
        # Task 1: Completed (100% progress)
        t1 = Task(project_id=self.p1.id, user_id=self.user1.id, title="Completed Task", status=WorkStatus.COMPLETED)

        # Task 2: In-progress with low progress (<25%)
        t2 = Task(
            project_id=self.p1.id,
            user_id=self.user1.id,
            title="Stalled Task",
            status=WorkStatus.IN_PROGRESS,
            priority=TaskPriority.HIGH,
            deadline=datetime.now(timezone.utc) + timedelta(days=2),
        )
        self.db.add_all([t1, t2])
        self.db.commit()
        self.db.refresh(t1)
        self.db.refresh(t2)

        # 4 phases for t1 (all completed)
        for i in range(4):
            self.db.add(Phase(task_id=t1.id, title=f"Ph {i}", status=WorkStatus.COMPLETED, order_index=i))

        # 5 phases for t2 (0 completed -> 0% progress)
        for i in range(5):
            self.db.add(Phase(task_id=t2.id, title=f"Ph {i}", status=WorkStatus.TODO, order_index=i))
        self.db.commit()

        mock_provider = MockAIProvider()
        result = get_progress_insights(self.db, self.user1.id, provider=mock_provider)

        self.assertIn("2 tasks", result.summary)
        self.assertGreaterEqual(len(result.insights), 2)

        types = [item.type for item in result.insights]
        self.assertIn("positive", types)
        self.assertIn("progress", types)

    def test_authorization_isolates_user_data(self):
        # Task in Secret Project (User 2)
        t_sec = Task(project_id=self.p_other.id, user_id=self.user2.id, title="Secret Task", status=WorkStatus.TODO)
        self.db.add(t_sec)
        self.db.commit()

        # User 1 has no tasks; cannot see User 2's tasks
        mock_provider = MockAIProvider()
        res_u1 = get_progress_insights(self.db, self.user1.id, provider=mock_provider)
        self.assertEqual(res_u1.summary, "Not enough task data for meaningful AI insights yet.")

        # User 1 requesting User 2's project raises 404
        with self.assertRaises(HTTPException) as cm:
            get_progress_insights(self.db, self.user1.id, project_id=self.p_other.id, provider=mock_provider)
        self.assertEqual(cm.exception.status_code, 404)

    def test_router_endpoint_execution(self):
        from app.analytics.router import get_progress_insights as endpoint_fn

        # Task for user 1
        t = Task(project_id=self.p1.id, user_id=self.user1.id, title="Test Task", status=WorkStatus.COMPLETED)
        self.db.add(t)
        self.db.commit()
        self.db.refresh(t)
        self.db.add(Phase(task_id=t.id, title="Phase 1", status=WorkStatus.COMPLETED, order_index=0))
        self.db.commit()

        mock_provider = MockAIProvider()
        response = endpoint_fn(
            project_id=None,
            current_user=self.user1,
            db=self.db,
            ai_provider=mock_provider,
        )
        self.assertIsNotNone(response.summary)
        self.assertIsInstance(response.insights, list)


if __name__ == "__main__":
    unittest.main()
