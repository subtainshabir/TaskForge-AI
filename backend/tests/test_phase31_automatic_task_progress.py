import unittest

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.enums import TaskPriority, WorkStatus
from app.models.phase import Phase
from app.models.project import Project
from app.models.task import Task
from app.models.user import User
from app.tasks import service
from app.tasks.schemas import PhaseCreate, PhaseUpdate, TaskResponse


class TestAutomaticTaskProgress(unittest.TestCase):
    def setUp(self):
        self.db = SessionLocal()
        self.user = self.db.execute(
            select(User).where(User.email == "phase31_test@example.com")
        ).scalar_one_or_none()
        if not self.user:
            self.user = User(
                email="phase31_test@example.com",
                password_hash="hashed_pw_test",
                name="Phase 31 Test User",
            )
            self.db.add(self.user)
            self.db.commit()
            self.db.refresh(self.user)

        self.project = Project(
            name="Phase 31 Test Project",
            user_id=self.user.id,
            description="Testing Phase 31 Automatic Task Progress",
        )
        self.db.add(self.project)
        self.db.commit()
        self.db.refresh(self.project)

        self.task = Task(
            project_id=self.project.id,
            user_id=self.user.id,
            title="Authentication System",
            description="Build authentication system",
            status=WorkStatus.IN_PROGRESS,
            priority=TaskPriority.HIGH,
        )
        self.db.add(self.task)
        self.db.commit()
        self.db.refresh(self.task)

    def tearDown(self):
        if self.project and self.project.id:
            p = self.db.get(Project, self.project.id)
            if p:
                self.db.delete(p)
                self.db.commit()
        self.db.close()

    def test_no_phases_progress_is_zero(self):
        # Scenario 1: No phases -> 0%
        prog = service.calculate_task_progress(self.db, self.task.id)
        self.assertEqual(prog, 0)

        task_data = service.get_owned_task(self.db, self.user.id, self.task.id)
        self.assertEqual(task_data.progress, 0)

        # Even if task status is completed, with 0 phases progress is 0%
        task_data.status = WorkStatus.COMPLETED
        self.db.commit()
        resp = TaskResponse.model_validate(task_data)
        self.assertEqual(resp.progress, 0)
        self.assertEqual(resp.status, "completed")

    def test_one_of_four_completed_progress_is_25(self):
        # Scenario 2: 1 of 4 completed -> 25%
        p1 = service.create_phase(self.db, self.user.id, self.task.id, PhaseCreate(title="Phase 1", status="completed"))
        p2 = service.create_phase(self.db, self.user.id, self.task.id, PhaseCreate(title="Phase 2", status="todo"))
        p3 = service.create_phase(self.db, self.user.id, self.task.id, PhaseCreate(title="Phase 3", status="todo"))
        p4 = service.create_phase(self.db, self.user.id, self.task.id, PhaseCreate(title="Phase 4", status="in_progress"))

        prog = service.calculate_task_progress(self.db, self.task.id)
        self.assertEqual(prog, 25)

        task_data = service.get_owned_task(self.db, self.user.id, self.task.id)
        self.assertEqual(task_data.progress, 25)
        resp = TaskResponse.model_validate(task_data)
        self.assertEqual(resp.progress, 25)

    def test_two_of_five_completed_progress_is_40(self):
        # Scenario 3: 2 of 5 completed -> 40%
        p1 = service.create_phase(self.db, self.user.id, self.task.id, PhaseCreate(title="Database", status="completed"))
        p2 = service.create_phase(self.db, self.user.id, self.task.id, PhaseCreate(title="Models", status="completed"))
        p3 = service.create_phase(self.db, self.user.id, self.task.id, PhaseCreate(title="JWT", status="todo"))
        p4 = service.create_phase(self.db, self.user.id, self.task.id, PhaseCreate(title="Login API", status="todo"))
        p5 = service.create_phase(self.db, self.user.id, self.task.id, PhaseCreate(title="Frontend Login", status="todo"))

        prog = service.calculate_task_progress(self.db, self.task.id)
        self.assertEqual(prog, 40)

        task_data = service.get_owned_task(self.db, self.user.id, self.task.id)
        self.assertEqual(task_data.progress, 40)

    def test_three_of_five_completed_progress_is_60(self):
        # Scenario 4: 3 of 5 completed -> 60%
        p1 = service.create_phase(self.db, self.user.id, self.task.id, PhaseCreate(title="Database", status="completed"))
        p2 = service.create_phase(self.db, self.user.id, self.task.id, PhaseCreate(title="Models", status="completed"))
        p3 = service.create_phase(self.db, self.user.id, self.task.id, PhaseCreate(title="JWT", status="completed"))
        p4 = service.create_phase(self.db, self.user.id, self.task.id, PhaseCreate(title="Login API", status="in_progress"))
        p5 = service.create_phase(self.db, self.user.id, self.task.id, PhaseCreate(title="Frontend Login", status="todo"))

        prog = service.calculate_task_progress(self.db, self.task.id)
        self.assertEqual(prog, 60)

        task_data = service.get_owned_task(self.db, self.user.id, self.task.id)
        self.assertEqual(task_data.progress, 60)

    def test_all_phases_completed_progress_is_100_and_task_status_independent(self):
        # Scenario 5: All phases completed -> 100%
        # But task status MUST remain in_progress (NOT auto-completed)
        self.task.status = WorkStatus.IN_PROGRESS
        self.db.commit()

        p1 = service.create_phase(self.db, self.user.id, self.task.id, PhaseCreate(title="P1", status="completed"))
        p2 = service.create_phase(self.db, self.user.id, self.task.id, PhaseCreate(title="P2", status="completed"))
        p3 = service.create_phase(self.db, self.user.id, self.task.id, PhaseCreate(title="P3", status="completed"))

        task_data = service.get_owned_task(self.db, self.user.id, self.task.id)
        self.assertEqual(task_data.progress, 100)
        self.assertEqual(task_data.status, WorkStatus.IN_PROGRESS)

    def test_reopen_phase_decreases_task_progress(self):
        # Scenario 6: Reopen phase decreases task progress
        p1 = service.create_phase(self.db, self.user.id, self.task.id, PhaseCreate(title="P1", status="completed"))
        p2 = service.create_phase(self.db, self.user.id, self.task.id, PhaseCreate(title="P2", status="completed"))
        p3 = service.create_phase(self.db, self.user.id, self.task.id, PhaseCreate(title="P3", status="completed"))

        self.assertEqual(service.calculate_task_progress(self.db, self.task.id), 100)

        # Reopen P2 to in_progress -> 2 of 3 = 67%
        service.update_phase(self.db, self.user.id, self.task.id, p2.id, PhaseUpdate(status="in_progress"))
        task_data = service.get_owned_task(self.db, self.user.id, self.task.id)
        self.assertEqual(task_data.progress, 67)

    def test_add_phase_recalculates_task_progress(self):
        # Scenario 7: Add phase recalculates task progress
        # 3 completed of 5 total = 60%
        for i in range(3):
            service.create_phase(self.db, self.user.id, self.task.id, PhaseCreate(title=f"Comp {i}", status="completed"))
        for i in range(2):
            service.create_phase(self.db, self.user.id, self.task.id, PhaseCreate(title=f"Todo {i}", status="todo"))

        self.assertEqual(service.calculate_task_progress(self.db, self.task.id), 60)

        # Add 1 new phase -> 3 completed of 6 total = 50%
        service.create_phase(self.db, self.user.id, self.task.id, PhaseCreate(title="New Phase", status="todo"))
        task_data = service.get_owned_task(self.db, self.user.id, self.task.id)
        self.assertEqual(task_data.progress, 50)

    def test_delete_phase_recalculates_task_progress(self):
        # Scenario 8: Delete phase recalculates task progress
        # 3 completed of 5 total = 60%
        comp_phases = [
            service.create_phase(self.db, self.user.id, self.task.id, PhaseCreate(title=f"C {i}", status="completed"))
            for i in range(3)
        ]
        todo_phases = [
            service.create_phase(self.db, self.user.id, self.task.id, PhaseCreate(title=f"T {i}", status="todo"))
            for i in range(2)
        ]
        self.assertEqual(service.calculate_task_progress(self.db, self.task.id), 60)

        # Delete 1 incomplete phase: 3 / 4 = 75%
        service.delete_phase(self.db, self.user.id, self.task.id, todo_phases[0].id)
        task_data = service.get_owned_task(self.db, self.user.id, self.task.id)
        self.assertEqual(task_data.progress, 75)

        # Delete 1 completed phase: 2 / 3 = 67%
        service.delete_phase(self.db, self.user.id, self.task.id, comp_phases[0].id)
        task_data = service.get_owned_task(self.db, self.user.id, self.task.id)
        self.assertEqual(task_data.progress, 67)

    def test_list_tasks_and_list_global_tasks_batch_progress(self):
        # Scenario 9: Multiple tasks batch progress calculation without N+1
        task2 = Task(
            project_id=self.project.id,
            user_id=self.user.id,
            title="Second Task",
            status=WorkStatus.TODO,
            priority=TaskPriority.LOW,
        )
        self.db.add(task2)
        self.db.commit()
        self.db.refresh(task2)

        # task has 1 completed phase of 2 = 50%
        service.create_phase(self.db, self.user.id, self.task.id, PhaseCreate(title="A", status="completed"))
        service.create_phase(self.db, self.user.id, self.task.id, PhaseCreate(title="B", status="todo"))

        # task2 has 3 completed phases of 3 = 100%
        service.create_phase(self.db, self.user.id, task2.id, PhaseCreate(title="X", status="completed"))
        service.create_phase(self.db, self.user.id, task2.id, PhaseCreate(title="Y", status="completed"))
        service.create_phase(self.db, self.user.id, task2.id, PhaseCreate(title="Z", status="completed"))

        project_tasks = service.list_tasks(self.db, self.project.id)
        task_map = {t.id: t.progress for t in project_tasks}
        self.assertEqual(task_map[self.task.id], 50)
        self.assertEqual(task_map[task2.id], 100)

        global_tasks = service.list_user_tasks(self.db, self.user.id)
        global_map = {t.id: t.progress for t in global_tasks}
        self.assertEqual(global_map[self.task.id], 50)
        self.assertEqual(global_map[task2.id], 100)
