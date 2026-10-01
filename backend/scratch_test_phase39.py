import json
import urllib.request
from app.db.session import SessionLocal
from app.models.user import User
from app.models.note import Note
from app.core.security import create_access_token

def main():
    db = SessionLocal()
    user = db.query(User).filter(User.email == 'phase38_demo@example.com').first()
    if not user:
        print("User not found")
        return

    note = db.query(Note).filter(Note.user_id == user.id, Note.title == 'Sprint 39 Extraction Test Note').first()
    if not note:
        note = Note(
            user_id=user.id,
            title='Sprint 39 Extraction Test Note',
            content="""<h2>Sprint Kickoff & Architecture Decision Record</h2>
<p>We decided to use <b>PostgreSQL</b> for our database and <b>FastAPI</b> for the backend service.</p>
<p>Lead architect Alice and backend engineer Bob agreed that JWT tokens will expire in 30 minutes.</p>
<ul class="note-checklist">
  <li class="note-checklist-item" data-checked="false"><input type="checkbox"> Implement note extraction API [High priority]</li>
  <li class="note-checklist-item" data-checked="true"><input type="checkbox" checked> Set up Alembic migrations</li>
</ul>
<blockquote>Target completion date discussed is October 15. Next team sync on Friday.</blockquote>
<pre class="note-code-block"><code>DATABASE_URL = postgresql+psycopg://localhost:5432/taskforge</code></pre>
<p>Follow-up: Investigate Redis connection pooling before production deployment.</p>"""
        )
        db.add(note)
        db.commit()
        db.refresh(note)

    token = create_access_token(str(user.id))

    print("--- 1. Testing Live AI Note Extraction ---")
    req = urllib.request.Request(
        f"http://127.0.0.1:8000/api/v1/notes/{note.id}/ai/extract",
        data=b"",
        headers={"Authorization": f"Bearer {token}"},
        method="POST"
    )

    try:
        with urllib.request.urlopen(req) as resp:
            print("Status code:", resp.getcode())
            res_json = json.loads(resp.read().decode())
            print("Extraction Response:")
            print(json.dumps(res_json, indent=2))
            
            # Check note unmodified
            db.refresh(note)
            print("Note content unchanged:", "Sprint Kickoff" in note.content)
            
            # Verify fields
            assert len(res_json.get("decisions", [])) > 0, "Expected decisions"
            assert len(res_json.get("action_items", [])) > 0, "Expected action items"
            assert len(res_json.get("technical_terms", [])) > 0, "Expected technical terms"
            print("Extraction schema assertions passed!")
    except urllib.error.HTTPError as e:
        print("HTTP error:", e.code, e.read().decode())
        return
    except Exception as e:
        print("Error:", e)
        return

    print("\n--- 2. Testing Empty Note Extraction ---")
    empty_note = Note(user_id=user.id, title="Empty Note", content="")
    db.add(empty_note)
    db.commit()
    db.refresh(empty_note)

    req_empty = urllib.request.Request(
        f"http://127.0.0.1:8000/api/v1/notes/{empty_note.id}/ai/extract",
        data=b"",
        headers={"Authorization": f"Bearer {token}"},
        method="POST"
    )
    with urllib.request.urlopen(req_empty) as r_empty:
        print("Empty note status code:", r_empty.getcode())
        empty_res = json.loads(r_empty.read().decode())
        print("Empty note response action_items:", empty_res.get("action_items"))
        print("Empty note response decisions:", empty_res.get("decisions"))
        assert len(empty_res.get("action_items")) == 0
        assert len(empty_res.get("decisions")) == 0
    db.delete(empty_note)
    db.commit()

    print("\n--- 3. Testing Unauthorized Access ---")
    other_user = User(email="unauth_phase39@example.com", password_hash="dummy", name="Other")
    db.add(other_user)
    db.commit()
    db.refresh(other_user)
    unauth_token = create_access_token(str(other_user.id))

    req_unauth = urllib.request.Request(
        f"http://127.0.0.1:8000/api/v1/notes/{note.id}/ai/extract",
        data=b"",
        headers={"Authorization": f"Bearer {unauth_token}"},
        method="POST"
    )
    try:
        urllib.request.urlopen(req_unauth)
        print("UNAUTH FAILED: should have returned 404")
    except urllib.error.HTTPError as e:
        print("Unauthorized status code correctly returned:", e.code)
    
    db.delete(other_user)
    db.commit()
    db.close()
    print("\nAll live Phase 39 extraction tests PASSED!")

if __name__ == "__main__":
    main()
