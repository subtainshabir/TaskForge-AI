import { useState } from "react";
import { Plus, StickyNote } from "lucide-react";
import Card from "../../Card/Card.jsx";
import Button from "../../Button/Button.jsx";
import Modal from "../../Modal/Modal.jsx";
import NoteList from "../NoteList/NoteList.jsx";
import NoteForm from "../NoteForm/NoteForm.jsx";
import NoteModal from "../NoteModal/NoteModal.jsx";
import DeleteNoteDialog from "../DeleteNoteDialog/DeleteNoteDialog.jsx";
import { useNotes } from "../../../hooks/useNotes.js";
import { noteService } from "../../../services/noteService.js";
import { apiErrorMessage } from "../../../utils/apiErrorMessage.js";
import "./NotesSection.css";

function NotesSection({
  projectId = null,
  projectName = "",
  taskId = null,
  taskTitle = "",
  title = "Notes",
  description = "Capture thoughts, specifications, and scratchpads.",
  showProject = true,
  showTask = true,
}) {
  const { notes, isLoading, error, refetch, addNote, replaceNote, removeNote } = useNotes({
    projectId,
    taskId,
  });

  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [editingNote, setEditingNote] = useState(null);
  const [viewingNote, setViewingNote] = useState(null);
  const [deletingNote, setDeletingNote] = useState(null);

  const [isSaving, setIsSaving] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [formError, setFormError] = useState("");
  const [deleteError, setDeleteError] = useState("");

  async function handleCreate(payload) {
    setIsSaving(true);
    setFormError("");
    try {
      const created = await noteService.create(payload);
      addNote(created);
      setIsCreateOpen(false);
    } catch (err) {
      setFormError(apiErrorMessage(err, "Failed to create note."));
    } finally {
      setIsSaving(false);
    }
  }

  async function handleUpdate(payload) {
    if (!editingNote) return;
    setIsSaving(true);
    setFormError("");
    try {
      const updated = await noteService.update(editingNote.id, payload);
      replaceNote(updated);
      setEditingNote(null);
    } catch (err) {
      setFormError(apiErrorMessage(err, "Failed to update note."));
    } finally {
      setIsSaving(false);
    }
  }

  async function handleDelete() {
    if (!deletingNote) return;
    setIsDeleting(true);
    setDeleteError("");
    try {
      await noteService.remove(deletingNote.id);
      removeNote(deletingNote.id);
      setDeletingNote(null);
    } catch (err) {
      setDeleteError(apiErrorMessage(err, "Failed to delete note."));
    } finally {
      setIsDeleting(false);
    }
  }

  async function handleCheckboxToggle(noteId, updatedContent) {
    try {
      const updated = await noteService.update(noteId, { content: updatedContent });
      replaceNote(updated);
      if (viewingNote && viewingNote.id === noteId) {
        setViewingNote(updated);
      }
    } catch {
      // Ignore background sync failure
    }
  }

  return (
    <Card className="notes-section-card">
      <div className="notes-section__header">
        <div className="notes-section__title-group">
          <div className="notes-section__title-row">
            <StickyNote size={20} className="notes-section__icon" aria-hidden="true" />
            <h2 className="notes-section__title">{title}</h2>
            {notes.length > 0 && (
              <span className="notes-section__count-badge">{notes.length}</span>
            )}
          </div>
          {description && (
            <p className="notes-section__description">{description}</p>
          )}
        </div>
        <Button
          type="button"
          variant="primary"
          size="sm"
          onClick={() => {
            setFormError("");
            setIsCreateOpen(true);
          }}
        >
          <Plus size={16} aria-hidden="true" />
          Create Note
        </Button>
      </div>

      <NoteList
        notes={notes}
        isLoading={isLoading}
        error={error}
        onRetry={refetch}
        onView={(note) => setViewingNote(note)}
        onEdit={(note) => {
          setFormError("");
          setEditingNote(note);
        }}
        onDelete={(note) => {
          setDeleteError("");
          setDeletingNote(note);
        }}
        onCreate={() => {
          setFormError("");
          setIsCreateOpen(true);
        }}
        emptyTitle={
          taskId
            ? "No notes for this task yet"
            : projectId
            ? "No notes for this project yet"
            : "No notes yet"
        }
        emptyDescription={
          taskId
            ? "Keep research, snippets, and task-specific scratchpads here."
            : projectId
            ? "Organize meeting notes, project specs, and thoughts here."
            : "Capture ideas, references, and scratchpads."
        }
        showProject={showProject}
        showTask={showTask}
      />

      {/* Create Note Modal */}
      <Modal
        open={isCreateOpen}
        onClose={() => {
          setIsCreateOpen(false);
          setFormError("");
        }}
        title={taskId ? "Create Task Note" : projectId ? "Create Project Note" : "Create Note"}
      >
        <NoteForm
          initialProjectId={projectId}
          initialTaskId={taskId}
          lockProject={Boolean(projectId)}
          lockTask={Boolean(taskId)}
          submitLabel="Create Note"
          isSubmitting={isSaving}
          apiError={formError}
          onSubmit={handleCreate}
          onCancel={() => {
            setIsCreateOpen(false);
            setFormError("");
          }}
        />
      </Modal>

      {/* Edit Note Modal */}
      <Modal
        open={Boolean(editingNote)}
        onClose={() => {
          setEditingNote(null);
          setFormError("");
        }}
        title="Edit Note"
      >
        <NoteForm
          initialValues={editingNote}
          submitLabel="Save Changes"
          isSubmitting={isSaving}
          apiError={formError}
          onSubmit={handleUpdate}
          onCancel={() => {
            setEditingNote(null);
            setFormError("");
          }}
        />
      </Modal>

      {/* View Note Modal */}
      <NoteModal
        note={viewingNote}
        open={Boolean(viewingNote)}
        onClose={() => setViewingNote(null)}
        onCheckboxToggle={(updatedHtml) =>
          viewingNote && handleCheckboxToggle(viewingNote.id, updatedHtml)
        }
        onEdit={(note) => {
          setViewingNote(null);
          setFormError("");
          setEditingNote(note);
        }}
        onDelete={(note) => {
          setViewingNote(null);
          setDeleteError("");
          setDeletingNote(note);
        }}
      />

      {/* Delete Note Confirmation Dialog */}
      <DeleteNoteDialog
        note={deletingNote}
        open={Boolean(deletingNote)}
        isDeleting={isDeleting}
        apiError={deleteError}
        onConfirm={handleDelete}
        onCancel={() => {
          setDeletingNote(null);
          setDeleteError("");
        }}
      />
    </Card>
  );
}

export default NotesSection;
