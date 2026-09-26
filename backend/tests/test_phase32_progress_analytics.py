import unittest

from sqlalchemy import select

from app.analytics.service import get_progress_analytics
from app.db.session import SessionLocal
from app.models.enums import TaskPriority, WorkStatus
from app.models.phase import Phase
from app.models.project import Project
from app.models.task import Task
from app.models.user import User


class TestProgressAnalytics(unittest.TestCase):
    def setUp(self):
        self.db = SessionLocal()

        # User 1
        self.user1 = self.db.execute(
            select(User).where(User.email == "phase32_user1@example.com")
        ).scalar_one_or_none()
        if not self.user1:
            self.user1 = User(
                email="phase32_user1@example.com",
                password_hash="hashed_pw_1",
                name="Phase 32 User One",
            )
            self.db.add(self.user1)
            self.db.commit()
            self.db.refresh(self.user1)

        # User 2 (for authorization tests)
        self.user2 = self.db.execute(
            select(User).where(User.email == "phase32_user2@example.com")
        ).scalar_one_or_none()
        if not self.user2:
            self.user2 = User(
                email="phase32_user2@example.com",
                password_hash="hashed_pw_2",
                name="Phase 32 User Two",
            )
            self.db.add(self.user2)
            self.db.commit()
            self.db.refresh(self.user2)

        # User 1 Projects
        self.p1 = Project(name="Project Alpha", user_id=self.user1.id, description="Alpha project")
        self.p2 = Project(name="Project Beta", user_id=self.user1.id, description="Beta project")
        self.db.add_all([self.p1, self.p2])
        self.db.commit()
        self.db.refresh(self.p1)
        self.db.refresh(self.p2)

        # User 2 Project
        self.p_other = Project(name="Secret Project", user_id=self.user2.id)
        self.db.add(self.p_other)
        self.db.commit()
        self.db.refresh(self.p_other)

        # User 2 Task
        self.t_other = Task(
            project_id=self.p_other.id,
            user_id=self.user2.id,
            title="User 2 Secret Task",
            status=WorkStatus.COMPLETED,
        )
        self.db.add(self.t_other)
        self.db.commit()

    def tearDown(self):
        # Delete user 1 projects and user 2 projects
        for p_id in [self.p1.id, self.p2.id, self.p_other.id]:
            p = self.db.get(Project, p_id)
            if p:
                self.db.delete(p)
                self.db.commit()
        self.db.close()

    def test_empty_workspace_returns_zero_stats(self):
        analytics = get_progress_analytics(self.db, self.user1.id)
        self.assertEqual(analytics.overview.total_tasks, 0)
        self.assertEqual(analytics.overview.completed_tasks, 0)
        self.assertEqual(analytics.overview.in_progress_tasks, 0)
        self.assertEqual(analytics.overview.todo_tasks, 0)
        self.assertEqual(analytics.overview.average_progress, 0)
        self.assertEqual(analytics.progress_distribution.zero, 0)
        self.assertEqual(analytics.progress_distribution.complete, 0)
        self.assertEqual(len(analytics.projects), 2)  # Two empty projects
        for proj in analytics.projects:
            self.assertEqual(proj.total_tasks, 0)
            self.assertEqual(proj.completed_tasks, 0)
            self.assertEqual(proj.average_progress, 0)

    def test_status_breakdown_and_average_progress(self):
        # Task 1: No phases -> progress 0%, status todo
        t1 = Task(project_id=self.p1.id, user_id=self.user1.id, title="Task 1", status=WorkStatus.TODO)

        # Task 2: 2 phases (1 completed) -> progress 50%, status in_progress
        t2 = Task(project_id=self.p1.id, user_id=self.user1.id, title="Task 2", status=WorkStatus.IN_PROGRESS)
        self.db.add_all([t1, t2])
        self.db.commit()
        self.db.refresh(t2)

        ph1 = Phase(task_id=t2.id, title="Ph 1", status=WorkStatus.COMPLETED, order_index=0)
        ph2 = Phase(task_id=t2.id, title="Ph 2", status=WorkStatus.TODO, order_index=1)
        self.db.add_all([ph1, ph2])
        self.db.commit()

        # Task 3: 4 phases (4 completed) -> progress 100%, status completed
        t3 = Task(project_id=self.p2.id, user_id=self.user1.id, title="Task 3", status=WorkStatus.COMPLETED)
        self.db.add(t3)
        self.db.commit()
        self.db.refresh(t3)

        for i in range(4):
            self.db.add(Phase(task_id=t3.id, title=f"Ph {i}", status=WorkStatus.COMPLETED, order_index=i))
        self.db.commit()

        analytics = get_progress_analytics(self.db, self.user1.id)

        # Overview checks: 3 tasks total
        self.assertEqual(analytics.overview.total_tasks, 3)
        self.assertEqual(analytics.overview.completed_tasks, 1)
        self.assertEqual(analytics.overview.in_progress_tasks, 1)
        self.assertEqual(analytics.overview.todo_tasks, 1)
        self.assertEqual(analytics.status_breakdown.completed, 1)
        self.assertEqual(analytics.status_breakdown.in_progress, 1)
        self.assertEqual(analytics.status_breakdown.todo, 1)

        # Progress calculation:
        # Task 1: 0%
        # Task 2: 50%
        # Task 3: 100%
        # Average: (0 + 50 + 100) / 3 = 150 / 3 = 50%
        self.assertEqual(analytics.overview.average_progress, 50)

        # Distribution checks:
        self.assertEqual(analytics.progress_distribution.p0, 1)
        self.assertEqual(analytics.progress_distribution.p50_74, 1)
        self.assertEqual(analytics.progress_distribution.p100, 1)
        self.assertEqual(analytics.progress_distribution.zero, 1)
        self.assertEqual(analytics.progress_distribution.medium, 1)
        self.assertEqual(analytics.progress_distribution.complete, 1)

    def test_progress_distribution_ranges(self):
        # Create tasks covering 0%, 1-24%, 25-49%, 50-74%, 75-99%, 100%
        # 1. 0%: 0 of 4
        t0 = Task(project_id=self.p1.id, user_id=self.user1.id, title="T0", status=WorkStatus.TODO)
        # 2. 20%: 1 of 5 (1-24%)
        t_low = Task(project_id=self.p1.id, user_id=self.user1.id, title="T_low", status=WorkStatus.IN_PROGRESS)
        # 3. 40%: 2 of 5 (25-49%)
        t_mid1 = Task(project_id=self.p1.id, user_id=self.user1.id, title="T_mid1", status=WorkStatus.IN_PROGRESS)
        # 4. 60%: 3 of 5 (50-74%)
        t_mid2 = Task(project_id=self.p1.id, user_id=self.user1.id, title="T_mid2", status=WorkStatus.IN_PROGRESS)
        # 5. 80%: 4 of 5 (75-99%)
        t_high = Task(project_id=self.p1.id, user_id=self.user1.id, title="T_high", status=WorkStatus.IN_PROGRESS)
        # 6. 100%: 5 of 5
        t_100 = Task(project_id=self.p1.id, user_id=self.user1.id, title="T_100", status=WorkStatus.COMPLETED)

        self.db.add_all([t0, t_low, t_mid1, t_mid2, t_high, t_100])
        self.db.commit()

        # Phases for t_low (1/5 = 20%)
        for i in range(5):
            st = WorkStatus.COMPLETED if i < 1 else WorkStatus.TODO
            self.db.add(Phase(task_id=t_low.id, title=f"ph{i}", status=st, order_index=i))

        # Phases for t_mid1 (2/5 = 40%)
        for i in range(5):
            st = WorkStatus.COMPLETED if i < 2 else WorkStatus.TODO
            self.db.add(Phase(task_id=t_mid1.id, title=f"ph{i}", status=st, order_index=i))

        # Phases for t_mid2 (3/5 = 60%)
        for i in range(5):
            st = WorkStatus.COMPLETED if i < 3 else WorkStatus.TODO
            self.db.add(Phase(task_id=t_mid2.id, title=f"ph{i}", status=st, order_index=i))

        # Phases for t_high (4/5 = 80%)
        for i in range(5):
            st = WorkStatus.COMPLETED if i < 4 else WorkStatus.TODO
            self.db.add(Phase(task_id=t_high.id, title=f"ph{i}", status=st, order_index=i))

        # Phases for t_100 (5/5 = 100%)
        for i in range(5):
            self.db.add(Phase(task_id=t_100.id, title=f"ph{i}", status=WorkStatus.COMPLETED, order_index=i))

        self.db.commit()

        analytics = get_progress_analytics(self.db, self.user1.id)

        dist = analytics.progress_distribution
        self.assertEqual(dist.p0, 1)
        self.assertEqual(dist.p1_24, 1)
        self.assertEqual(dist.p25_49, 1)
        self.assertEqual(dist.p50_74, 1)
        self.assertEqual(dist.p75_99, 1)
        self.assertEqual(dist.p100, 1)

        self.assertEqual(dist.zero, 1)
        self.assertEqual(dist.low, 2)  # 20% + 40% = 2 tasks
        self.assertEqual(dist.medium, 1)  # 60%
        self.assertEqual(dist.high, 1)  # 80%
        self.assertEqual(dist.complete, 1)  # 100%

        # Check buckets
        bucket_map = {b.key: b for b in dist.buckets}
        self.assertEqual(bucket_map["0"].count, 1)
        self.assertEqual(bucket_map["1_24"].count, 1)
        self.assertEqual(bucket_map["25_49"].count, 1)
        self.assertEqual(bucket_map["50_74"].count, 1)
        self.assertEqual(bucket_map["75_99"].count, 1)
        self.assertEqual(bucket_map["100"].count, 1)

    def test_project_progress_summary_and_unfinished_ranking(self):
        # Project Alpha: 2 tasks, 0 completed -> 2 unfinished
        t_a1 = Task(project_id=self.p1.id, user_id=self.user1.id, title="A1", status=WorkStatus.TODO)
        t_a2 = Task(project_id=self.p1.id, user_id=self.user1.id, title="A2", status=WorkStatus.IN_PROGRESS)

        # Project Beta: 3 tasks, 2 completed -> 1 unfinished
        t_b1 = Task(project_id=self.p2.id, user_id=self.user1.id, title="B1", status=WorkStatus.COMPLETED)
        t_b2 = Task(project_id=self.p2.id, user_id=self.user1.id, title="B2", status=WorkStatus.COMPLETED)
        t_b3 = Task(project_id=self.p2.id, user_id=self.user1.id, title="B3", status=WorkStatus.TODO)

        self.db.add_all([t_a1, t_a2, t_b1, t_b2, t_b3])
        self.db.commit()

        analytics = get_progress_analytics(self.db, self.user1.id)

        # Project Alpha has 2 unfinished tasks; Beta has 1 unfinished task.
        # Projects should be sorted with Alpha first (most unfinished tasks)
        self.assertEqual(analytics.projects[0].name, "Project Alpha")
        self.assertEqual(analytics.projects[0].unfinished_tasks, 2)
        self.assertEqual(analytics.projects[0].total_tasks, 2)
        self.assertEqual(analytics.projects[0].completed_tasks, 0)
        self.assertEqual(analytics.projects[0].in_progress_tasks, 1)
        self.assertEqual(analytics.projects[0].todo_tasks, 1)

        self.assertEqual(analytics.projects[1].name, "Project Beta")
        self.assertEqual(analytics.projects[1].unfinished_tasks, 1)
        self.assertEqual(analytics.projects[1].total_tasks, 3)
        self.assertEqual(analytics.projects[1].completed_tasks, 2)

    def test_authorization_isolates_user_data(self):
        # User 1 has no tasks yet; User 2 has 1 completed task in Secret Project
        analytics_u1 = get_progress_analytics(self.db, self.user1.id)
        self.assertEqual(analytics_u1.overview.total_tasks, 0)
        self.assertEqual(len(analytics_u1.projects), 2)  # only Alpha and Beta
        project_names = [p.name for p in analytics_u1.projects]
        self.assertNotIn("Secret Project", project_names)

        analytics_u2 = get_progress_analytics(self.db, self.user2.id)
        self.assertEqual(analytics_u2.overview.total_tasks, 1)
        self.assertEqual(analytics_u2.overview.completed_tasks, 1)
        self.assertEqual(len(analytics_u2.projects), 1)
        self.assertEqual(analytics_u2.projects[0].name, "Secret Project")

    def test_filter_by_project_id(self):
        # Task in Project Alpha
        t_a = Task(project_id=self.p1.id, user_id=self.user1.id, title="A", status=WorkStatus.TODO)
        # Task in Project Beta
        t_b = Task(project_id=self.p2.id, user_id=self.user1.id, title="B", status=WorkStatus.COMPLETED)
        self.db.add_all([t_a, t_b])
        self.db.commit()

        # Query only Project Alpha
        analytics = get_progress_analytics(self.db, self.user1.id, project_id=self.p1.id)
        self.assertEqual(analytics.overview.total_tasks, 1)
        self.assertEqual(analytics.overview.todo_tasks, 1)
        self.assertEqual(analytics.overview.completed_tasks, 0)
        self.assertEqual(len(analytics.projects), 1)
        self.assertEqual(analytics.projects[0].name, "Project Alpha")

        # Query unauthorized project ID raises 404
        from fastapi import HTTPException
        with self.assertRaises(HTTPException) as cm:
            get_progress_analytics(self.db, self.user1.id, project_id=self.p_other.id)
        self.assertEqual(cm.exception.status_code, 404)

    def test_router_endpoint_execution(self):
        from app.analytics.router import get_progress_analytics as endpoint_fn
        response = endpoint_fn(
            project_id=None,
            current_user=self.user1,
            db=self.db,
        )
        self.assertIsNotNone(response.overview)
        self.assertIsNotNone(response.status_breakdown)
        self.assertIsNotNone(response.progress_distribution)
        self.assertIsInstance(response.projects, list)


if __name__ == "__main__":
    unittest.main()
