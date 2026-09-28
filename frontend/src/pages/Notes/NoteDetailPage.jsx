import { useCallback, useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import {
  ArrowLeft,
  Calendar,
  CheckSquare,
  Clock,
  FolderKanban,
  Pencil,
  Trash2,
  StickyNote,
} from "lucide-react";
import PageContainer from "../../components/PageContainer/PageContainer.jsx";
import Card from "../../components/Card/Card.jsx";
import Badge from "../../components/Badge/Badge.jsx";
import Button from "../../components/Button/Button.jsx";
import Modal from "../../components/Modal/Modal.jsx";
import Spinner from "../../components/Spinner/Spinner.jsx";
import { ErrorState } from "../../components/StatePanel/StatePanel.jsx";
import NoteForm from "../../components/notes/NoteForm/NoteForm.jsx";
import DeleteNoteDialog from "../../components/notes/DeleteNoteDialog/DeleteNoteDialog.jsx";
import { noteService } from "../../services/noteService.js";
import { apiErrorMessage } from "../../utils/apiErrorMessage.js";
import { formatAbsoluteDate, formatActivityTime } from "../../utils/date.js";
import "./NoteDetailPage.css";

function NoteDetailPage() {
  const { noteId } = useParams();
  const navigate = useNavigate();

  const [note, setNote] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");

  const [isEditOpen, setIsEditOpen] = useState(false);
  const [isDeleteOpen, setIsDeleteOpen] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [formError, setFormError] = useState("");
  const [deleteError, setDeleteError] = useState("");

  const loadNote = useCallback(async () => {
    setIsLoading(true);
    setError("");
    try {
      const data = await noteService.get(noteId);
      setNote(data);
    } catch (err) {
      setError(
        apiErrorMessage(
          err,
          "This note doesn't exist or you don't have permission to access it."
        )
      );
    } finally {
      setIsLoading(false);
    }
  }, [noteId]);

  useEffect(() => {
    loadNote();
  }, [loadNote]);

  async function handleUpdate(payload) {
    setIsSaving(true);
    setFormError("");
    try {
      const updated = await noteService.update(noteId, payload);
      setNote(updated);
      setIsEditOpen(false);
    } catch (err) {
      setFormError(apiErrorMessage(err, "Failed to update note."));
    } finally {
      setIsSaving(false);
    }
  }

  async function handleDelete() {
    setIsDeleting(true);
    setDeleteError("");
    try {
      await noteService.remove(noteId);
      navigate("/notes", { replace: true });
    } catch (err) {
      setDeleteError(apiErrorMessage(err, "Failed to delete note."));
    } finally {
      setIsDeleting(false);
    }
  }

  if (isLoading) {
    return (
      <PageContainer>
        <div className="note-detail__loading">
          <Spinner size="lg" label="Loading note details..." />
        </div>
      </PageContainer>
    );
  }

  if (error || !note) {
    return (
      <PageContainer>
        <Card>
          <ErrorState
            title="Note not found"
            description={
              error ||
              "This note doesn't exist or you don't have access to view it."
            }
            action={
              <Button variant="secondary" onClick={() => navigate("/notes")}>
                Back to Notes
              </Button>
            }
          />
        </Card>
      </PageContainer>
    );
  }

  const hasProject = Boolean(note.project_id);
  const hasTask = Boolean(note.task_id);

  return (
    <PageContainer
      title={note.title}
      actions={
        <div className="note-detail__actions">
          <Button variant="secondary" onClick={() => setIsEditOpen(true)}>
            <Pencil size={16} aria-hidden="true" />
            Edit
          </Button>
          <Button variant="danger" onClick={() => setIsDeleteOpen(true)}>
            <Trash2 size={16} aria-hidden="true" />
            Delete
          </Button>
        </div>
      }
    >
      <Link to="/notes" className="note-detail__back">
        <ArrowLeft size={14} aria-hidden="true" />
        Back to Notes
      </Link>

      <Card className="note-detail__card">
        <div className="note-detail__meta">
          <div className="note-detail__associations">
            {hasProject && (
              <Link
                to={`/projects/${note.project_id}`}
                className="note-detail__badge-link"
              >
                <Badge variant="neutral">
                  <FolderKanban size={13} aria-hidden="true" />
                  <span>{note.project_name || `Project #${note.project_id}`}</span>
                </Badge>
              </Link>
            )}

            {hasTask && (
              <Link
                to={
                  note.project_id
                    ? `/projects/${note.project_id}/tasks/${note.task_id}`
                    : `/tasks`
                }
                className="note-detail__badge-link"
              >
                <Badge variant="neutral" className="note-detail__task-badge">
                  <CheckSquare size={13} aria-hidden="true" />
                  <span>{note.task_title || `Task #${note.task_id}`}</span>
                </Badge>
              </Link>
            )}

            {!hasProject && !hasTask && (
              <span className="note-detail__general-badge">General Note</span>
            )}
          </div>

          <div className="note-detail__timestamps">
            <span title={`Created on ${formatAbsoluteDate(note.created_at)}`}>
              <Calendar size={13} aria-hidden="true" />
              Created {formatAbsoluteDate(note.created_at)}
            </span>
            <span title={`Updated ${formatActivityTime(note.updated_at)}`}>
              <Clock size={13} aria-hidden="true" />
              Updated {formatActivityTime(note.updated_at)}
            </span>
          </div>
        </div>

        <div className="note-detail__body">
          {note.content ? (
            <p className="note-detail__content">{note.content}</p>
          ) : (
            <p className="note-detail__empty-content">
              This note does not have any content. Click Edit to add details.
            </p>
          )}
        </div>
      </Card>

      {/* Edit Note Modal */}
      <Modal
        open={isEditOpen}
        onClose={() => {
          setIsEditOpen(false);
          setFormError("");
        }}
        title="Edit Note"
      >
        <NoteForm
          initialValues={note}
          submitLabel="Save Changes"
          isSubmitting={isSaving}
          apiError={formError}
          onSubmit={handleUpdate}
          onCancel={() => {
            setIsEditOpen(false);
            setFormError("");
          }}
        />
      </Modal>

      {/* Delete Note Confirmation Dialog */}
      <DeleteNoteDialog
        note={note}
        open={isDeleteOpen}
        isDeleting={isDeleting}
        apiError={deleteError}
        onConfirm={handleDelete}
        onCancel={() => {
          setIsDeleteOpen(false);
          setDeleteError("");
        }}
      />
    </PageContainer>
  );
}

export default NoteDetailPage;
