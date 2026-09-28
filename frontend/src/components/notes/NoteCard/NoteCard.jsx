import { FolderKanban, CheckSquare, Clock, Pencil, Trash2, StickyNote } from "lucide-react";
import { Link } from "react-router-dom";
import Badge from "../../Badge/Badge.jsx";
import { formatActivityTime } from "../../../utils/date.js";
import "./NoteCard.css";

function NoteCard({
  note,
  onView,
  onEdit,
  onDelete,
  showProject = true,
  showTask = true,
}) {
  const hasProject = Boolean(note.project_id);
  const hasTask = Boolean(note.task_id);

  function handleCardClick() {
    if (onView) onView(note);
  }

  function handleKeyDown(event) {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      if (onView) onView(note);
    }
  }

  return (
    <article
      className="note-card"
      tabIndex={0}
      role="button"
      onClick={handleCardClick}
      onKeyDown={handleKeyDown}
      aria-label={`Open note: ${note.title}`}
    >
      <div className="note-card__header">
        <div className="note-card__title-group">
          <StickyNote size={18} className="note-card__icon" aria-hidden="true" />
          <h3 className="note-card__title" title={note.title}>
            {note.title}
          </h3>
        </div>
        <div className="note-card__actions" onClick={(e) => e.stopPropagation()}>
          {onEdit && (
            <button
              type="button"
              className="note-card__action-btn"
              onClick={() => onEdit(note)}
              aria-label={`Edit ${note.title}`}
              title="Edit note"
            >
              <Pencil size={15} aria-hidden="true" />
            </button>
          )}
          {onDelete && (
            <button
              type="button"
              className="note-card__action-btn note-card__action-btn--danger"
              onClick={() => onDelete(note)}
              aria-label={`Delete ${note.title}`}
              title="Delete note"
            >
              <Trash2 size={15} aria-hidden="true" />
            </button>
          )}
        </div>
      </div>

      <div className="note-card__content">
        {note.content ? (
          <p className="note-card__preview">{note.content}</p>
        ) : (
          <p className="note-card__empty-text">No additional content</p>
        )}
      </div>

      <div className="note-card__footer" onClick={(e) => e.stopPropagation()}>
        <div className="note-card__badges">
          {showProject && hasProject && (
            <Link
              to={`/projects/${note.project_id}`}
              className="note-card__badge-link"
              title={`Project: ${note.project_name || note.project_id}`}
            >
              <Badge variant="neutral" className="note-card__badge">
                <FolderKanban size={12} aria-hidden="true" />
                <span className="note-card__badge-text">
                  {note.project_name || `Project #${note.project_id}`}
                </span>
              </Badge>
            </Link>
          )}

          {showTask && hasTask && (
            <Link
              to={
                note.project_id
                  ? `/projects/${note.project_id}/tasks/${note.task_id}`
                  : `/tasks`
              }
              className="note-card__badge-link"
              title={`Task: ${note.task_title || note.task_id}`}
            >
              <Badge variant="neutral" className="note-card__badge note-card__badge--task">
                <CheckSquare size={12} aria-hidden="true" />
                <span className="note-card__badge-text">
                  {note.task_title || `Task #${note.task_id}`}
                </span>
              </Badge>
            </Link>
          )}

          {!hasProject && !hasTask && (
            <span className="note-card__general-tag">General</span>
          )}
        </div>

        <div className="note-card__time" title={`Updated ${note.updated_at}`}>
          <Clock size={12} aria-hidden="true" />
          <span>{formatActivityTime(note.updated_at)}</span>
        </div>
      </div>
    </article>
  );
}

export default NoteCard;
