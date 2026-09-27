from datetime import datetime, timezone
import unittest

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.enums import ProjectStatus, TaskPriority, WorkStatus
from app.models.note import Note
from app.models.project import Project
from app.models.task import Task
from app.models.user import User
from app.notes import service
from app.notes.router import (
    create_note_endpoint,
    delete_note_endpoint,
    get_note_endpoint,
    list_notes_endpoint,
    update_note_endpoint,
)
from app.notes.schemas import NoteCreate, NoteResponse, NoteUpdate
from app.projects.router import get_project_notes_endpoint
from app.tasks.router import get_task_notes_endpoint


class TestNotesBackend(unittest.TestCase):
    def setUp(self):
        self.db = SessionLocal()

        # User 1
        self.user1 = self.db.execute(
            select(User).where(User.email == "phase35_user1@example.com")
        ).scalar_one_or_none()
        if not self.user1:
            self.user1 = User(
                email="phase35_user1@example.com",
                password_hash="hashed_pw_1",
                name="Phase 35 User One",
            )
            self.db.add(self.user1)
            self.db.commit()
            self.db.refresh(self.user1)

        # User 2 (unauthorized attacker)
        self.user2 = self.db.execute(
            select(User).where(User.email == "phase35_user2@example.com")
        ).scalar_one_or_none()
        if not self.user2:
            self.user2 = User(
                email="phase35_user2@example.com",
                password_hash="hashed_pw_2",
                name="Phase 35 User Two",
            )
            self.db.add(self.user2)
            self.db.commit()
            self.db.refresh(self.user2)

        # Project 1 for User 1
        self.p1 = Project(
            name="Project One",
            user_id=self.user1.id,
            description="First project for User 1",
            status=ProjectStatus.ACTIVE,
        )
        self.db.add(self.p1)

        # Project 2 for User 1
        self.p2 = Project(
            name="Project Two",
            user_id=self.user1.id,
            description="Second project for User 1",
            status=ProjectStatus.ACTIVE,
        )
        self.db.add(self.p2)

        # Project for User 2
        self.p_user2 = Project(
            name="User2 Secret Project",
            user_id=self.user2.id,
            description="Private project",
            status=ProjectStatus.ACTIVE,
        )
        self.db.add(self.p_user2)
        self.db.commit()
        self.db.refresh(self.p1)
        self.db.refresh(self.p2)
        self.db.refresh(self.p_user2)

        # Task 1 in Project 1 (User 1)
        self.t1 = Task(
            project_id=self.p1.id,
            user_id=self.user1.id,
            title="Authentication implementation",
            status=WorkStatus.TODO,
            priority=TaskPriority.HIGH,
        )
        self.db.add(self.t1)

        # Task for User 2
        self.t_user2 = Task(
            project_id=self.p_user2.id,
            user_id=self.user2.id,
            title="User 2 Secret Task",
            status=WorkStatus.TODO,
            priority=TaskPriority.LOW,
        )
        self.db.add(self.t_user2)
        self.db.commit()
        self.db.refresh(self.t1)
        self.db.refresh(self.t_user2)

    def tearDown(self):
        # Clean up projects (which cascades to tasks and notes)
        for p_id in [self.p1.id, self.p2.id, self.p_user2.id]:
            p = self.db.get(Project, p_id)
            if p:
                self.db.delete(p)
                self.db.commit()

        # Clean up any leftover general notes for test users
        leftover = list(
            self.db.execute(
                select(Note).where(Note.user_id.in_([self.user1.id, self.user2.id]))
            ).scalars().all()
        )
        for n in leftover:
            self.db.delete(n)
        if leftover:
            self.db.commit()

        self.db.close()

    def test_create_general_note(self):
        """User can create a general note unassociated with a project or task."""
        payload = NoteCreate(title="General architecture ideas", content="Microservices vs modular monolith")
        note = service.create_note(self.db, self.user1.id, payload)

        self.assertIsNotNone(note.id)
        self.assertEqual(note.user_id, self.user1.id)
        self.assertIsNone(note.project_id)
        self.assertIsNone(note.task_id)
        self.assertEqual(note.title, "General architecture ideas")
        self.assertEqual(note.content, "Microservices vs modular monolith")
        self.assertIsNotNone(note.created_at)
        self.assertIsNotNone(note.updated_at)

    def test_create_project_note(self):
        """User can create a note associated with an owned project."""
        payload = NoteCreate(
            title="Project design guidelines",
            content="Use consistent color tokens and accessible contrasts",
            project_id=self.p1.id,
        )
        note = service.create_note(self.db, self.user1.id, payload)

        self.assertEqual(note.user_id, self.user1.id)
        self.assertEqual(note.project_id, self.p1.id)
        self.assertIsNone(note.task_id)
        self.assertEqual(note.project_name, "Project One")

    def test_create_task_note(self):
        """User can create a note associated with a task, inheriting its project_id."""
        payload = NoteCreate(
            title="JWT expiry note",
            content="Token should expire in 30 minutes, refresh token in 7 days",
            task_id=self.t1.id,
        )
        note = service.create_note(self.db, self.user1.id, payload)

        self.assertEqual(note.user_id, self.user1.id)
        self.assertEqual(note.task_id, self.t1.id)
        # Should have inherited task's project_id
        self.assertEqual(note.project_id, self.p1.id)
        self.assertEqual(note.task_title, "Authentication implementation")

    def test_task_note_with_explicit_matching_project(self):
        """Specifying matching project_id and task_id succeeds."""
        payload = NoteCreate(
            title="Valid task note",
            content="Belongs to p1 and t1",
            project_id=self.p1.id,
            task_id=self.t1.id,
        )
        note = service.create_note(self.db, self.user1.id, payload)
        self.assertEqual(note.project_id, self.p1.id)
        self.assertEqual(note.task_id, self.t1.id)

    def test_inconsistent_task_and_project_rejected(self):
        """Specifying task_id belonging to p1 but project_id of p2 raises 400."""
        payload = NoteCreate(
            title="Mismatched note",
            content="Inconsistent relationship",
            project_id=self.p2.id,  # Task t1 is in p1, not p2
            task_id=self.t1.id,
        )
        with self.assertRaises(HTTPException) as ctx:
            service.create_note(self.db, self.user1.id, payload)
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("Task does not belong to the specified project", ctx.exception.detail)

    def test_cannot_create_note_for_foreign_project(self):
        """User 1 cannot create a note for User 2's project."""
        payload = NoteCreate(
            title="Hacker note",
            content="Trying to attach to another user's project",
            project_id=self.p_user2.id,
        )
        with self.assertRaises(HTTPException) as ctx:
            service.create_note(self.db, self.user1.id, payload)
        self.assertEqual(ctx.exception.status_code, 404)

    def test_cannot_create_note_for_foreign_task(self):
        """User 1 cannot create a note for User 2's task."""
        payload = NoteCreate(
            title="Hacker note",
            content="Trying to attach to another user's task",
            task_id=self.t_user2.id,
        )
        with self.assertRaises(HTTPException) as ctx:
            service.create_note(self.db, self.user1.id, payload)
        self.assertEqual(ctx.exception.status_code, 404)

    def test_schema_title_validation(self):
        """Title must not be empty or whitespace only."""
        with self.assertRaises(ValidationError):
            NoteCreate(title="")

        with self.assertRaises(ValidationError):
            NoteCreate(title="   ")

        with self.assertRaises(ValidationError):
            NoteUpdate(title="")

        with self.assertRaises(ValidationError):
            NoteUpdate(title="   ")

        # Whitespace stripping
        n = NoteCreate(title="  Trimmed Title  ")
        self.assertEqual(n.title, "Trimmed Title")

    def test_update_note(self):
        """User can update title and content of an owned note."""
        note = service.create_note(
            self.db,
            self.user1.id,
            NoteCreate(title="Original title", content="Original content"),
        )
        updated = service.update_note(
            self.db,
            note,
            NoteUpdate(title="Updated title", content="Updated content"),
        )
        self.assertEqual(updated.title, "Updated title")
        self.assertEqual(updated.content, "Updated content")

    def test_delete_note(self):
        """User can delete an owned note."""
        note = service.create_note(
            self.db,
            self.user1.id,
            NoteCreate(title="To be deleted", content="Ephemeral"),
        )
        note_id = note.id
        service.delete_note(self.db, note)

        with self.assertRaises(HTTPException) as ctx:
            service.get_owned_note(self.db, self.user1.id, note_id)
        self.assertEqual(ctx.exception.status_code, 404)

    def test_unauthorized_user_cannot_access_or_modify(self):
        """User 2 cannot read, update, or delete User 1's note."""
        note = service.create_note(
            self.db,
            self.user1.id,
            NoteCreate(title="User 1 Confidential Note", content="Top Secret"),
        )

        # User 2 read attempt
        with self.assertRaises(HTTPException) as ctx:
            service.get_owned_note(self.db, self.user2.id, note.id)
        self.assertEqual(ctx.exception.status_code, 404)

        # User 2 endpoint read
        with self.assertRaises(HTTPException) as ctx:
            get_note_endpoint(note.id, current_user=self.user2, db=self.db)
        self.assertEqual(ctx.exception.status_code, 404)

        # User 2 update attempt
        with self.assertRaises(HTTPException) as ctx:
            update_note_endpoint(
                note.id,
                payload=NoteUpdate(title="Malicious update"),
                current_user=self.user2,
                db=self.db,
            )
        self.assertEqual(ctx.exception.status_code, 404)

        # User 2 delete attempt
        with self.assertRaises(HTTPException) as ctx:
            delete_note_endpoint(note.id, current_user=self.user2, db=self.db)
        self.assertEqual(ctx.exception.status_code, 404)

    def test_list_notes_and_filters(self):
        """Verify list_notes supports project_id, task_id, general_only, and search filters."""
        # 1 General Note
        n_gen = service.create_note(
            self.db,
            self.user1.id,
            NoteCreate(title="Workspace Note", content="General reminder"),
        )
        # 1 Project Note
        n_proj = service.create_note(
            self.db,
            self.user1.id,
            NoteCreate(title="Project Specs", content="Sprint roadmap", project_id=self.p1.id),
        )
        # 1 Task Note
        n_task = service.create_note(
            self.db,
            self.user1.id,
            NoteCreate(title="Task Bug Analysis", content="Bug in auth token", task_id=self.t1.id),
        )

        # All notes for User 1
        all_notes = service.list_notes(self.db, self.user1.id)
        self.assertGreaterEqual(len(all_notes), 3)

        # Filter general only
        gen_notes = service.list_notes(self.db, self.user1.id, general_only=True)
        self.assertEqual(len(gen_notes), 1)
        self.assertEqual(gen_notes[0].id, n_gen.id)

        # Filter by project
        proj_notes = service.list_notes(self.db, self.user1.id, project_id=self.p1.id)
        # Note: both n_proj and n_task have project_id=self.p1.id
        self.assertEqual(len(proj_notes), 2)

        # Filter by task
        task_notes = service.list_notes(self.db, self.user1.id, task_id=self.t1.id)
        self.assertEqual(len(task_notes), 1)
        self.assertEqual(task_notes[0].id, n_task.id)

        # Search filter
        search_notes = service.list_notes(self.db, self.user1.id, search="Sprint")
        self.assertEqual(len(search_notes), 1)
        self.assertEqual(search_notes[0].id, n_proj.id)

    def test_scoped_project_and_task_notes_endpoints(self):
        """Verify GET /projects/{id}/notes and GET /tasks/{id}/notes endpoints."""
        n1 = service.create_note(
            self.db,
            self.user1.id,
            NoteCreate(title="Architecture Spec", project_id=self.p1.id),
        )
        n2 = service.create_note(
            self.db,
            self.user1.id,
            NoteCreate(title="Task Checkpoint", task_id=self.t1.id),
        )

        # Project scoped endpoint
        proj_notes = get_project_notes_endpoint(self.p1.id, current_user=self.user1, db=self.db)
        note_ids = [n.id for n in proj_notes]
        self.assertIn(n1.id, note_ids)
        self.assertIn(n2.id, note_ids)

        # User 2 cannot access User 1's project notes
        with self.assertRaises(HTTPException) as ctx:
            get_project_notes_endpoint(self.p1.id, current_user=self.user2, db=self.db)
        self.assertEqual(ctx.exception.status_code, 404)

        # Task scoped endpoint
        task_notes = get_task_notes_endpoint(self.t1.id, current_user=self.user1, db=self.db)
        self.assertEqual(len(task_notes), 1)
        self.assertEqual(task_notes[0].id, n2.id)

        # User 2 cannot access User 1's task notes
        with self.assertRaises(HTTPException) as ctx:
            get_task_notes_endpoint(self.t1.id, current_user=self.user2, db=self.db)
        self.assertEqual(ctx.exception.status_code, 404)

    def test_cascade_delete_on_project_removal(self):
        """When a project is deleted, its associated notes are deleted via CASCADE."""
        note = service.create_note(
            self.db,
            self.user1.id,
            NoteCreate(title="Project note to be cascaded", project_id=self.p2.id),
        )
        note_id = note.id

        # Delete project
        self.db.delete(self.p2)
        self.db.commit()

        # Note should be deleted automatically
        found = self.db.get(Note, note_id)
        self.assertIsNone(found)

    def test_cascade_delete_on_task_removal(self):
        """When a task is deleted, its associated notes are deleted via CASCADE."""
        note = service.create_note(
            self.db,
            self.user1.id,
            NoteCreate(title="Task note to be cascaded", task_id=self.t1.id),
        )
        note_id = note.id

        # Delete task
        self.db.delete(self.t1)
        self.db.commit()

        # Note should be deleted automatically
        found = self.db.get(Note, note_id)
        self.assertIsNone(found)

    def test_router_crud_endpoints(self):
        """Verify router endpoints create, read, update, list, and delete notes."""
        # Create
        created = create_note_endpoint(
            NoteCreate(title="Router Test Note", content="Via router"),
            current_user=self.user1,
            db=self.db,
        )
        self.assertEqual(created.title, "Router Test Note")
        resp = NoteResponse.model_validate(created)
        self.assertEqual(resp.title, "Router Test Note")

        # Read
        fetched = get_note_endpoint(created.id, current_user=self.user1, db=self.db)
        self.assertEqual(fetched.id, created.id)

        # List
        listed = list_notes_endpoint(current_user=self.user1, db=self.db)
        self.assertTrue(any(n.id == created.id for n in listed))

        # Update
        updated = update_note_endpoint(
            created.id,
            payload=NoteUpdate(content="Updated via router"),
            current_user=self.user1,
            db=self.db,
        )
        self.assertEqual(updated.content, "Updated via router")

        # Delete
        delete_note_endpoint(created.id, current_user=self.user1, db=self.db)
        with self.assertRaises(HTTPException) as ctx:
            get_note_endpoint(created.id, current_user=self.user1, db=self.db)
        self.assertEqual(ctx.exception.status_code, 404)


if __name__ == "__main__":
    unittest.main()
