import { StickyNote } from "lucide-react";
import NoteCard from "../NoteCard/NoteCard.jsx";
import Spinner from "../../Spinner/Spinner.jsx";
import { EmptyState, ErrorState } from "../../StatePanel/StatePanel.jsx";
import Button from "../../Button/Button.jsx";
import "./NoteList.css";

function NoteList({
  notes = [],
  isLoading = false,
  error = "",
  onRetry,
  onView,
  onEdit,
  onDelete,
  onCreate,
  emptyTitle = "No notes yet",
  emptyDescription = "Keep thoughts, references, and scratchpads organized with notes.",
  showProject = true,
  showTask = true,
}) {
  if (isLoading) {
    return (
      <div className="note-list__loading">
        <Spinner size="md" label="Loading notes..." />
      </div>
    );
  }

  if (error) {
    return (
      <ErrorState
        title="Unable to load notes"
        description={error}
        action={
          onRetry ? (
            <Button variant="secondary" onClick={onRetry}>
              Try again
            </Button>
          ) : null
        }
      />
    );
  }

  if (notes.length === 0) {
    return (
      <EmptyState
        icon={<StickyNote size={36} aria-hidden="true" />}
        title={emptyTitle}
        description={emptyDescription}
        action={
          onCreate ? (
            <Button variant="primary" onClick={onCreate}>
              Create Note
            </Button>
          ) : null
        }
      />
    );
  }

  return (
    <div className="note-list-grid">
      {notes.map((note) => (
        <NoteCard
          key={note.id}
          note={note}
          onView={onView}
          onEdit={onEdit}
          onDelete={onDelete}
          showProject={showProject}
          showTask={showTask}
        />
      ))}
    </div>
  );
}

export default NoteList;
