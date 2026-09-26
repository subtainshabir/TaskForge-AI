import unittest
from datetime import datetime, timezone

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.enums import TaskPriority, WorkStatus
from app.models.phase import Phase
from app.models.project import Project
from app.models.task import Task
from app.models.user import User
from app.tasks import service
from app.tasks.schemas import PhaseCreate, PhaseUpdate


class TestPhaseCompletionSystem(unittest.TestCase):
    def setUp(self):
        self.db = SessionLocal()
        # Find or create test user
        self.user = self.db.execute(
            select(User).where(User.email == "phase30_test@example.com")
        ).scalar_one_or_none()
        if not self.user:
            self.user = User(
                email="phase30_test@example.com",
                password_hash="hashed_pw_test",
                name="Phase 30 Test User",
            )
            self.db.add(self.user)
            self.db.commit()
            self.db.refresh(self.user)

        # Another user for ownership checks
        self.other_user = self.db.execute(
            select(User).where(User.email == "phase30_other@example.com")
        ).scalar_one_or_none()
        if not self.other_user:
            self.other_user = User(
                email="phase30_other@example.com",
                password_hash="hashed_pw_test",
                name="Phase 30 Other User",
            )
            self.db.add(self.other_user)
            self.db.commit()
            self.db.refresh(self.other_user)

        self.project = Project(
            name="Phase 30 Test Project",
            user_id=self.user.id,
            description="Testing Phase 30 Phase Completion System",
        )
        self.db.add(self.project)
        self.db.commit()
        self.db.refresh(self.project)

        self.task = Task(
            project_id=self.project.id,
            user_id=self.user.id,
            title="Authentication Feature",
            description="Build authentication feature",
            status=WorkStatus.TODO,
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

    def test_create_phase_defaults_and_completion(self):
        # 1. Default creation -> status="todo", completed_at=None, progress=0
        phase1 = service.create_phase(
            self.db,
            self.user.id,
            self.task.id,
            PhaseCreate(title="Phase 1 Planning", description="Initial plan"),
        )
        self.assertEqual(phase1.status, WorkStatus.TODO)
        self.assertIsNone(phase1.completed_at)
        self.assertEqual(phase1.progress, 0)
        self.assertEqual(phase1.order_index, 0)

        # 2. Created directly as completed -> completed_at is set, progress=100
        phase2 = service.create_phase(
            self.db,
            self.user.id,
            self.task.id,
            PhaseCreate(title="Phase 2 Design", status="completed"),
        )
        self.assertEqual(phase2.status, WorkStatus.COMPLETED)
        self.assertIsNotNone(phase2.completed_at)
        self.assertEqual(phase2.progress, 100)
        self.assertEqual(phase2.order_index, 1)

    def test_invalid_status_rejected_on_create_and_update(self):
        # Invalid status on create via schema validation
        with self.assertRaises(ValidationError):
            PhaseCreate(title="Invalid Phase", status="invalid_status")

        with self.assertRaises(ValidationError):
            PhaseCreate(title="Blocked Phase", status="blocked")

        # Invalid status on update via schema validation
        with self.assertRaises(ValidationError):
            PhaseUpdate(status="cancelled")

        with self.assertRaises(ValidationError):
            PhaseUpdate(status="unknown")

    def test_complete_phase_sets_timestamp_and_records_activity(self):
        phase = service.create_phase(
            self.db,
            self.user.id,
            self.task.id,
            PhaseCreate(title="Authentication Flow", status="todo"),
        )
        self.assertIsNone(phase.completed_at)
        self.assertEqual(phase.status, WorkStatus.TODO)

        before_update = datetime.now(timezone.utc)
        updated = service.update_phase(
            self.db,
            self.user.id,
            self.task.id,
            phase.id,
            PhaseUpdate(status="completed"),
        )
        after_update = datetime.now(timezone.utc)

        self.assertEqual(updated.status, WorkStatus.COMPLETED)
        self.assertEqual(updated.progress, 100)
        self.assertIsNotNone(updated.completed_at)
        self.assertTrue(before_update <= updated.completed_at <= after_update)

        # Verify activity was recorded
        activities = service.list_task_activities(self.db, self.user.id, self.task.id)
        completion_act = next(
            (a for a in activities if a.activity_type == "phase_completed"), None
        )
        self.assertIsNotNone(completion_act)
        self.assertEqual(
            completion_act.description, f'Phase "{phase.title}" completed'
        )

    def test_reopen_phase_resets_timestamp_and_records_activity(self):
        phase = service.create_phase(
            self.db,
            self.user.id,
            self.task.id,
            PhaseCreate(title="Database Setup", status="completed"),
        )
        self.assertIsNotNone(phase.completed_at)

        # Reopen to in_progress
        reopened = service.update_phase(
            self.db,
            self.user.id,
            self.task.id,
            phase.id,
            PhaseUpdate(status="in_progress"),
        )
        self.assertEqual(reopened.status, WorkStatus.IN_PROGRESS)
        self.assertIsNone(reopened.completed_at)
        self.assertEqual(reopened.progress, 0)

        # Verify activity recorded
        activities = service.list_task_activities(self.db, self.user.id, self.task.id)
        reopened_act = next(
            (a for a in activities if a.activity_type == "phase_reopened"), None
        )
        self.assertIsNotNone(reopened_act)
        self.assertEqual(reopened_act.description, f'Phase "{phase.title}" reopened')

        # Complete again, then reopen to todo
        service.update_phase(
            self.db,
            self.user.id,
            self.task.id,
            phase.id,
            PhaseUpdate(status="completed"),
        )
        reopened_todo = service.update_phase(
            self.db,
            self.user.id,
            self.task.id,
            phase.id,
            PhaseUpdate(status="todo"),
        )
        self.assertEqual(reopened_todo.status, WorkStatus.TODO)
        self.assertIsNone(reopened_todo.completed_at)

    def test_status_transition_todo_to_in_progress(self):
        phase = service.create_phase(
            self.db,
            self.user.id,
            self.task.id,
            PhaseCreate(title="Testing Pipeline", status="todo"),
        )
        updated = service.update_phase(
            self.db,
            self.user.id,
            self.task.id,
            phase.id,
            PhaseUpdate(status="in_progress"),
        )
        self.assertEqual(updated.status, WorkStatus.IN_PROGRESS)
        self.assertIsNone(updated.completed_at)

        activities = service.list_task_activities(self.db, self.user.id, self.task.id)
        update_act = next(
            (a for a in activities if a.activity_type == "phase_updated"), None
        )
        self.assertIsNotNone(update_act)
        self.assertIn("in progress", update_act.description.lower())

    def test_no_op_update_preserves_completed_at_and_avoids_duplicate_activity(self):
        phase = service.create_phase(
            self.db,
            self.user.id,
            self.task.id,
            PhaseCreate(title="API Integration", status="completed"),
        )
        original_completed_at = phase.completed_at
        self.assertIsNotNone(original_completed_at)

        # Count activities before no-op update
        activities_before = len(
            service.list_task_activities(self.db, self.user.id, self.task.id)
        )

        # Update with status="completed" again and title change
        updated = service.update_phase(
            self.db,
            self.user.id,
            self.task.id,
            phase.id,
            PhaseUpdate(title="API Integration Enhanced", status="completed"),
        )
        self.assertEqual(updated.completed_at, original_completed_at)
        self.assertEqual(updated.title, "API Integration Enhanced")

        # Activities count should not include duplicate phase_completed
        activities_after = service.list_task_activities(
            self.db, self.user.id, self.task.id
        )
        phase_completed_count = sum(
            1 for a in activities_after if a.activity_type == "phase_completed"
        )
        self.assertEqual(phase_completed_count, 0)  # created as completed, not updated to completed

    def test_phase_ordering_preserved(self):
        p1 = service.create_phase(
            self.db, self.user.id, self.task.id, PhaseCreate(title="1. Planning", order_index=0)
        )
        p2 = service.create_phase(
            self.db, self.user.id, self.task.id, PhaseCreate(title="2. Development", order_index=1)
        )
        p3 = service.create_phase(
            self.db, self.user.id, self.task.id, PhaseCreate(title="3. Deployment", order_index=2)
        )

        # Complete the 3rd phase first
        service.update_phase(
            self.db, self.user.id, self.task.id, p3.id, PhaseUpdate(status="completed")
        )

        phases = service.get_task_phases(self.db, self.user.id, self.task.id)
        self.assertEqual(len(phases), 3)
        self.assertEqual([p.id for p in phases], [p1.id, p2.id, p3.id])
        self.assertEqual([p.order_index for p in phases], [0, 1, 2])
        self.assertEqual(phases[2].status, WorkStatus.COMPLETED)

    def test_progress_calculation(self):
        # Initially 0 phases -> 0%
        prog = service.sync_task_progress(self.db, self.task)
        self.assertEqual(prog, 0)

        # Add 1 completed phase -> 1/1 = 100%
        p1 = service.create_phase(
            self.db, self.user.id, self.task.id, PhaseCreate(title="P1", status="completed")
        )
        self.assertEqual(self.task.progress, 100)

        # Add 1 todo phase -> 1/2 = 50%
        p2 = service.create_phase(
            self.db, self.user.id, self.task.id, PhaseCreate(title="P2", status="todo")
        )
        self.assertEqual(self.task.progress, 50)

        # Add 1 more todo phase -> 1/3 = 33%
        p3 = service.create_phase(
            self.db, self.user.id, self.task.id, PhaseCreate(title="P3", status="todo")
        )
        self.assertEqual(self.task.progress, 33)

        # Complete P2 -> 2/3 = 67%
        service.update_phase(
            self.db, self.user.id, self.task.id, p2.id, PhaseUpdate(status="completed")
        )
        self.assertEqual(self.task.progress, 67)

        # Complete P3 -> 3/3 = 100%
        service.update_phase(
            self.db, self.user.id, self.task.id, p3.id, PhaseUpdate(status="completed")
        )
        self.assertEqual(self.task.progress, 100)

        # Reopen P1 -> 2/3 = 67%
        service.update_phase(
            self.db, self.user.id, self.task.id, p1.id, PhaseUpdate(status="in_progress")
        )
        self.assertEqual(self.task.progress, 67)

        # Delete P2 (which was completed) -> 1 completed out of 2 = 50%
        service.delete_phase(self.db, self.user.id, self.task.id, p2.id)
        self.assertEqual(self.task.progress, 50)

        # Delete remaining phases -> 0%
        service.delete_phase(self.db, self.user.id, self.task.id, p1.id)
        service.delete_phase(self.db, self.user.id, self.task.id, p3.id)
        self.assertEqual(self.task.progress, 0)

    def test_task_status_not_auto_completed_on_100_percent_phase_progress(self):
        # Rule 19: Completing all phases must NOT mark the task as completed
        self.task.status = WorkStatus.IN_PROGRESS
        self.db.commit()

        p1 = service.create_phase(
            self.db, self.user.id, self.task.id, PhaseCreate(title="Only Phase", status="todo")
        )
        self.assertEqual(self.task.status, WorkStatus.IN_PROGRESS)

        # Complete phase
        service.update_phase(
            self.db, self.user.id, self.task.id, p1.id, PhaseUpdate(status="completed")
        )

        self.db.refresh(self.task)
        self.assertEqual(self.task.progress, 100)
        # Task status MUST still be in_progress (NOT completed)
        self.assertEqual(self.task.status, WorkStatus.IN_PROGRESS)

    def test_ownership_and_validation(self):
        phase = service.create_phase(
            self.db, self.user.id, self.task.id, PhaseCreate(title="Secure Phase")
        )

        # Other user cannot access or update
        with self.assertRaises(HTTPException) as ctx:
            service.update_phase(
                self.db,
                self.other_user.id,
                self.task.id,
                phase.id,
                PhaseUpdate(status="completed"),
            )
        self.assertEqual(ctx.exception.status_code, 404)

        # Non-existent phase
        with self.assertRaises(HTTPException) as ctx:
            service.update_phase(
                self.db,
                self.user.id,
                self.task.id,
                999999,
                PhaseUpdate(status="completed"),
            )
        self.assertEqual(ctx.exception.status_code, 404)

    def test_router_update_phase_endpoint(self):
        from app.tasks.router import update_phase as update_phase_endpoint

        phase = service.create_phase(
            self.db, self.user.id, self.task.id, PhaseCreate(title="Endpoint Phase")
        )
        response = update_phase_endpoint(
            task_id=self.task.id,
            phase_id=phase.id,
            payload=PhaseUpdate(status="completed"),
            current_user=self.user,
            db=self.db,
        )
        self.assertEqual(response.status, "completed")
        self.assertIsNotNone(response.completed_at)
        self.assertEqual(response.progress, 100)

        # Reopen via endpoint
        reopen_response = update_phase_endpoint(
            task_id=self.task.id,
            phase_id=phase.id,
            payload=PhaseUpdate(status="todo"),
            current_user=self.user,
            db=self.db,
        )
        self.assertEqual(reopen_response.status, "todo")
        self.assertIsNone(reopen_response.completed_at)
