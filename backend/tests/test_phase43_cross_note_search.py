import json
import unittest

from fastapi import HTTPException
from sqlalchemy import select

from app.ai.base import AIProvider
from app.ai.factory import MockAIProvider
from app.ai.note_search.prompts import (
    NOTE_SEARCH_SYSTEM_PROMPT,
    build_note_search_prompt,
)
from app.ai.note_search.schemas import (
    NoteAISearchRequest,
    NoteAISearchResponse,
    NoteSearchSource,
)
from app.ai.note_search.service import (
    extract_json,
    extract_search_keywords,
    rank_note_relevance,
    search_notes_ai,
)
from app.db.session import SessionLocal
from app.models.note import Note
from app.models.user import User
from app.notes.router import search_notes_ai_endpoint


class DummyAIProvider(AIProvider):
    def __init__(self, configured: bool = True, response: str = ""):
        self._configured = configured
        self._response = response
        self.call_count = 0

    def is_configured(self) -> bool:
        return self._configured

    def complete(self, prompt: str, system_prompt: str = None, **kwargs) -> str:
        self.call_count += 1
        if not self._configured:
            raise RuntimeError("Provider not configured")
        return self._response


class TestPhase43CrossNoteSearch(unittest.TestCase):
    def setUp(self):
        self.db = SessionLocal()

        # User 1
        self.user1 = self.db.execute(
            select(User).where(User.email == "phase43_user1@example.com")
        ).scalar_one_or_none()
        if not self.user1:
            self.user1 = User(
                email="phase43_user1@example.com",
                password_hash="hashed_pw_1",
                name="Phase 43 User One",
            )
            self.db.add(self.user1)
            self.db.commit()
            self.db.refresh(self.user1)

        # User 2 (for cross-user isolation test)
        self.user2 = self.db.execute(
            select(User).where(User.email == "phase43_user2@example.com")
        ).scalar_one_or_none()
        if not self.user2:
            self.user2 = User(
                email="phase43_user2@example.com",
                password_hash="hashed_pw_2",
                name="Phase 43 User Two",
            )
            self.db.add(self.user2)
            self.db.commit()
            self.db.refresh(self.user2)

        # Clean existing test notes for reproducible tests
        existing_notes = self.db.execute(
            select(Note).where(Note.user_id.in_([self.user1.id, self.user2.id]))
        ).scalars().all()
        for n in existing_notes:
            self.db.delete(n)
        self.db.commit()

        # Create notes for User 1
        self.note_postgres = Note(
            user_id=self.user1.id,
            title="Database Architecture",
            content="We use PostgreSQL as our primary relational database. Connection pooling uses psycopg.",
        )
        self.note_auth = Note(
            user_id=self.user1.id,
            title="Authentication Notes",
            content="The authentication system uses JWT and FastAPI. Access tokens expire in 30 minutes.",
        )
        self.note_security = Note(
            user_id=self.user1.id,
            title="API Security",
            content="All API endpoints require JWT authentication. Password hashing uses bcrypt.",
        )
        self.note_rich = Note(
            user_id=self.user1.id,
            title="Frontend Guidelines",
            content="<h2>Design System</h2><p>Follow modern styling.</p><ul class=\"note-checklist\"><li data-checked=\"true\"><input type=\"checkbox\" checked/> Use CSS variables</li><li data-checked=\"false\"><input type=\"checkbox\"/> Audit contrast</li></ul><pre><code>const theme = 'dark';</code></pre>",
        )
        self.db.add_all([self.note_postgres, self.note_auth, self.note_security, self.note_rich])

        # Create note for User 2 (Secret Note)
        self.note_user2 = Note(
            user_id=self.user2.id,
            title="User 2 Secret Project",
            content="PostgreSQL confidential database credentials and private keys.",
        )
        self.db.add(self.note_user2)
        self.db.commit()

        self.db.refresh(self.note_postgres)
        self.db.refresh(self.note_auth)
        self.db.refresh(self.note_security)
        self.db.refresh(self.note_rich)
        self.db.refresh(self.note_user2)

    def tearDown(self):
        self.db.close()

    def test_search_keywords_extraction(self):
        """Test extraction of search keywords, removing punctuation and stop words."""
        cleaned, keywords = extract_search_keywords("Which notes mention PostgreSQL?")
        self.assertIn("postgresql", keywords)
        self.assertNotIn("which", keywords)
        self.assertNotIn("mention", keywords)

        cleaned2, keywords2 = extract_search_keywords("Which notes discuss JWT authentication?")
        self.assertIn("jwt", keywords2)
        self.assertIn("authentication", keywords2)

    def test_rank_note_relevance(self):
        """Verify relevance ranking scores title and content matches deterministically."""
        clean_phrase, keywords = extract_search_keywords("PostgreSQL")
        score_pg = rank_note_relevance(self.note_postgres, clean_phrase, keywords)
        score_auth = rank_note_relevance(self.note_auth, clean_phrase, keywords)

        self.assertGreater(score_pg, 0)
        self.assertEqual(score_auth, 0)

    def test_search_single_note_match(self):
        """Search matching exactly one note returns answer and citation."""
        provider = DummyAIProvider(
            configured=True,
            response=json.dumps({
                "answer": "PostgreSQL is mentioned in Database Architecture as the primary relational database.",
                "source_note_ids": [self.note_postgres.id],
            }),
        )

        res = search_notes_ai(
            db=self.db,
            user_id=self.user1.id,
            question="Which notes mention PostgreSQL?",
            provider=provider,
        )

        self.assertIn("PostgreSQL", res.answer)
        self.assertEqual(len(res.sources), 1)
        self.assertEqual(res.sources[0].note_id, self.note_postgres.id)
        self.assertEqual(res.sources[0].title, "Database Architecture")
        self.assertEqual(provider.call_count, 1)

    def test_search_multiple_notes_match(self):
        """Search matching multiple notes returns answer and citations for both notes."""
        provider = DummyAIProvider(
            configured=True,
            response=json.dumps({
                "answer": "JWT authentication is discussed in two notes.",
                "source_note_ids": [self.note_auth.id, self.note_security.id],
            }),
        )

        res = search_notes_ai(
            db=self.db,
            user_id=self.user1.id,
            question="Which notes discuss JWT authentication?",
            provider=provider,
        )

        self.assertEqual(res.answer, "JWT authentication is discussed in two notes.")
        self.assertEqual(len(res.sources), 2)
        source_ids = [s.note_id for s in res.sources]
        self.assertIn(self.note_auth.id, source_ids)
        self.assertIn(self.note_security.id, source_ids)

    def test_empty_search_results_no_ai_call(self):
        """When no notes match, return immediate response without invoking AI."""
        provider = DummyAIProvider(configured=True, response="Should not be called")

        res = search_notes_ai(
            db=self.db,
            user_id=self.user1.id,
            question="Which notes mention Kubernetes cluster deployment?",
            provider=provider,
        )

        self.assertEqual(res.answer, "No relevant notes were found.")
        self.assertEqual(res.sources, [])
        self.assertEqual(provider.call_count, 0)

    def test_missing_information_in_matching_notes(self):
        """When notes match query keywords but don't contain enough info to answer specific question."""
        provider = DummyAIProvider(
            configured=True,
            response=json.dumps({
                "answer": "The available notes do not contain enough information to answer this question.",
                "source_note_ids": [],
            }),
        )

        res = search_notes_ai(
            db=self.db,
            user_id=self.user1.id,
            question="What is the database administrator's salary for PostgreSQL?",
            provider=provider,
        )

        self.assertIn("not contain enough information", res.answer.lower())
        self.assertEqual(res.sources, [])

    def test_cross_user_isolation(self):
        """Ensure User 1 cannot search or receive User 2's notes."""
        provider = MockAIProvider()

        # User 1 searches for PostgreSQL (User 1 has Database Architecture, User 2 has User 2 Secret Project)
        res1 = search_notes_ai(
            db=self.db,
            user_id=self.user1.id,
            question="Which notes mention PostgreSQL?",
            provider=provider,
        )

        # None of User 2's notes should ever appear in User 1's results
        for src in res1.sources:
            self.assertNotEqual(src.note_id, self.note_user2.id)
            self.assertNotEqual(src.title, "User 2 Secret Project")

        # User 2 searches for Database
        res2 = search_notes_ai(
            db=self.db,
            user_id=self.user2.id,
            question="Which notes mention PostgreSQL?",
            provider=provider,
        )
        self.assertTrue(any(s.note_id == self.note_user2.id for s in res2.sources))
        self.assertFalse(any(s.note_id == self.note_postgres.id for s in res2.sources))

    def test_question_validation_empty(self):
        """Reject empty and whitespace-only questions with 400 Bad Request."""
        provider = DummyAIProvider(configured=True)

        with self.assertRaises(HTTPException) as ctx:
            search_notes_ai(db=self.db, user_id=self.user1.id, question="   ", provider=provider)
        self.assertEqual(ctx.exception.status_code, 400)

        with self.assertRaises(HTTPException) as ctx2:
            search_notes_ai(db=self.db, user_id=self.user1.id, question="", provider=provider)
        self.assertEqual(ctx2.exception.status_code, 400)

    def test_question_validation_too_long(self):
        """Reject questions longer than 1000 characters with 400 Bad Request."""
        provider = DummyAIProvider(configured=True)
        long_q = "What is " + "a" * 1005

        with self.assertRaises(HTTPException) as ctx:
            search_notes_ai(db=self.db, user_id=self.user1.id, question=long_q, provider=provider)
        self.assertEqual(ctx.exception.status_code, 400)

    def test_unconfigured_ai_provider(self):
        """Return 503 Service Unavailable if matching notes exist but AI is not configured."""
        provider = DummyAIProvider(configured=False)

        with self.assertRaises(HTTPException) as ctx:
            search_notes_ai(
                db=self.db,
                user_id=self.user1.id,
                question="Which notes mention PostgreSQL?",
                provider=provider,
            )
        self.assertEqual(ctx.exception.status_code, 503)

    def test_provider_timeout_error(self):
        """Raise 504 Gateway Timeout when provider times out."""
        class TimeoutProvider(AIProvider):
            def is_configured(self):
                return True
            def complete(self, *args, **kwargs):
                raise TimeoutError("Timed out")

        with self.assertRaises(HTTPException) as ctx:
            search_notes_ai(
                db=self.db,
                user_id=self.user1.id,
                question="Which notes mention PostgreSQL?",
                provider=TimeoutProvider(),
            )
        self.assertEqual(ctx.exception.status_code, 504)

    def test_rich_notes_search(self):
        """Verify searching rich-text notes with HTML checklist items works."""
        provider = DummyAIProvider(
            configured=True,
            response=json.dumps({
                "answer": "Frontend Guidelines covers CSS variables and contrast auditing.",
                "source_note_ids": [self.note_rich.id],
            }),
        )

        res = search_notes_ai(
            db=self.db,
            user_id=self.user1.id,
            question="Which notes mention CSS variables?",
            provider=provider,
        )

        self.assertEqual(len(res.sources), 1)
        self.assertEqual(res.sources[0].note_id, self.note_rich.id)

    def test_notes_remain_unmodified(self):
        """Confirm that Cross-Note AI Search never modifies note titles, contents, or timestamps."""
        orig_content = self.note_postgres.content
        orig_updated_at = self.note_postgres.updated_at

        provider = MockAIProvider()
        search_notes_ai(
            db=self.db,
            user_id=self.user1.id,
            question="Which notes mention PostgreSQL?",
            provider=provider,
        )

        refreshed = self.db.execute(
            select(Note).where(Note.id == self.note_postgres.id)
        ).scalar_one()

        self.assertEqual(refreshed.content, orig_content)
        self.assertEqual(refreshed.updated_at, orig_updated_at)

    def test_endpoint_integration(self):
        """Test search_notes_ai_endpoint directly with NoteAISearchRequest."""
        provider = MockAIProvider()
        req = NoteAISearchRequest(question="Which notes mention PostgreSQL?")

        res = search_notes_ai_endpoint(
            payload=req,
            current_user=self.user1,
            db=self.db,
            ai_provider=provider,
        )

        self.assertIsInstance(res, NoteAISearchResponse)
        self.assertIn("PostgreSQL", res.answer)
        self.assertTrue(any(s.note_id == self.note_postgres.id for s in res.sources))


if __name__ == "__main__":
    unittest.main()
