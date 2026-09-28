import { useEffect, useMemo, useState } from "react";
import { Plus, StickyNote, Search, X, ArrowUpDown, Filter } from "lucide-react";
import PageContainer from "../../components/PageContainer/PageContainer.jsx";
import Card from "../../components/Card/Card.jsx";
import Button from "../../components/Button/Button.jsx";
import Modal from "../../components/Modal/Modal.jsx";
import NoteList from "../../components/notes/NoteList/NoteList.jsx";
import NoteForm from "../../components/notes/NoteForm/NoteForm.jsx";
import NoteModal from "../../components/notes/NoteModal/NoteModal.jsx";
import DeleteNoteDialog from "../../components/notes/DeleteNoteDialog/DeleteNoteDialog.jsx";
import { useNotes } from "../../hooks/useNotes.js";
import { useDebouncedValue } from "../../hooks/useDebouncedValue.js";
import { noteService } from "../../services/noteService.js";
import { projectService } from "../../services/projectService.js";
import { apiErrorMessage } from "../../utils/apiErrorMessage.js";
import "./NotesPage.css";

function NotesPage() {
  const [projects, setProjects] = useState([]);
  const [selectedProjectFilter, setSelectedProjectFilter] = useState("");
  const [search, setSearch] = useState("");
  const [sortBy, setSortBy] = useState("updated_at");
  const [order, setOrder] = useState("desc");

  const debouncedSearch = useDebouncedValue(search, 300);

  // Compute params for useNotes
  const isGeneralOnly = selectedProjectFilter === "general";
  const projectIdParam =
    selectedProjectFilter && selectedProjectFilter !== "general"
      ? Number(selectedProjectFilter)
      : null;

  const {
    notes,
    isLoading,
    error,
    refetch,
    addNote,
    replaceNote,
    removeNote,
  } = useNotes({
    projectId: projectIdParam,
    generalOnly: isGeneralOnly,
    search: debouncedSearch,
    sortBy,
    order,
  });

  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [editingNote, setEditingNote] = useState(null);
  const [viewingNote, setViewingNote] = useState(null);
  const [deletingNote, setDeletingNote] = useState(null);

  const [isSaving, setIsSaving] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [formError, setFormError] = useState("");
  const [deleteError, setDeleteError] = useState("");

  // Load projects for project filter
  useEffect(() => {
    let isCurrent = true;
    projectService
      .list()
      .then((data) => {
        if (isCurrent) setProjects(data || []);
      })
      .catch(() => {
        if (isCurrent) setProjects([]);
      });
    return () => {
      isCurrent = false;
    };
  }, []);

  const hasActiveFilters = Boolean(search.trim() || selectedProjectFilter || sortBy !== "updated_at" || order !== "desc");

  function clearFilters() {
    setSearch("");
    setSelectedProjectFilter("");
    setSortBy("updated_at");
    setOrder("desc");
  }

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
    <PageContainer
      title="Notes"
      subtitle="Capture thoughts, project documentation, and task scratchpads"
      actions={
        <Button
          variant="primary"
          onClick={() => {
            setFormError("");
            setIsCreateOpen(true);
          }}
        >
          <Plus size={16} aria-hidden="true" />
          Create Note
        </Button>
      }
    >
      <div className="notes-page__controls">
        <div className="notes-page__search-box">
          <Search size={16} aria-hidden="true" />
          <input
            type="search"
            placeholder="Search notes by title or content..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            aria-label="Search notes"
          />
          {search && (
            <button
              type="button"
              className="notes-page__search-clear"
              onClick={() => setSearch("")}
              aria-label="Clear search"
            >
              <X size={14} aria-hidden="true" />
            </button>
          )}
        </div>

        <div className="notes-page__filters">
          <div className="notes-page__filter-group">
            <Filter size={14} className="notes-page__filter-icon" aria-hidden="true" />
            <select
              className="notes-page__select"
              value={selectedProjectFilter}
              onChange={(e) => setSelectedProjectFilter(e.target.value)}
              aria-label="Filter by project"
            >
              <option value="">All Projects & Notes</option>
              <option value="general">General Notes Only</option>
              {projects.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name}
                </option>
              ))}
            </select>
          </div>

          <div className="notes-page__filter-group">
            <ArrowUpDown size={14} className="notes-page__filter-icon" aria-hidden="true" />
            <select
              className="notes-page__select"
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value)}
              aria-label="Sort by"
            >
              <option value="updated_at">Last Updated</option>
              <option value="created_at">Date Created</option>
              <option value="title">Title</option>
            </select>

            <button
              type="button"
              className="notes-page__order-toggle"
              onClick={() => setOrder((prev) => (prev === "asc" ? "desc" : "asc"))}
              title={`Sorting ${order === "asc" ? "Ascending" : "Descending"}`}
              aria-label={`Toggle order: currently ${order}`}
            >
              {order === "asc" ? "ASC" : "DESC"}
            </button>
          </div>

          {hasActiveFilters && (
            <button
              type="button"
              className="notes-page__clear-btn"
              onClick={clearFilters}
            >
              Clear filters
            </button>
          )}
        </div>
      </div>

      <div className="notes-page__content">
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
            hasActiveFilters
              ? "No notes match your filters"
              : "No notes yet"
          }
          emptyDescription={
            hasActiveFilters
              ? "Try adjusting your search terms or clearing selected filters."
              : "Capture your ideas, documentation, and scratchpads to stay productive."
          }
          showProject={true}
          showTask={true}
        />
      </div>

      {/* Create Note Modal */}
      <Modal
        open={isCreateOpen}
        onClose={() => {
          setIsCreateOpen(false);
          setFormError("");
        }}
        title="Create Note"
      >
        <NoteForm
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
    </PageContainer>
  );
}

export default NotesPage;
