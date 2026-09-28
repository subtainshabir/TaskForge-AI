import { Link } from "react-router-dom";
import { FolderKanban, CheckSquare, Clock, Calendar, Pencil, Trash2, ExternalLink } from "lucide-react";
import Modal from "../../Modal/Modal.jsx";
import Button from "../../Button/Button.jsx";
import Badge from "../../Badge/Badge.jsx";
import RichTextViewer from "../RichTextViewer/RichTextViewer.jsx";
import { formatAbsoluteDate, formatActivityTime } from "../../../utils/date.js";
import "./NoteModal.css";

function NoteModal({
  note,
  open,
  onClose,
  onEdit,
  onDelete,
  onCheckboxToggle,
}) {
  if (!note) return null;

  const hasProject = Boolean(note.project_id);
  const hasTask = Boolean(note.task_id);

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={note.title}
      footer={
        <div className="note-modal__footer-actions">
          <Link
            to={`/notes/${note.id}`}
            className="note-modal__full-page-link"
            title="Open dedicated note page"
          >
            <ExternalLink size={14} aria-hidden="true" />
            <span>Dedicated page</span>
          </Link>
          <div className="note-modal__right-actions">
            {onDelete && (
              <Button
                type="button"
                variant="ghost"
                onClick={() => {
                  onClose();
                  onDelete(note);
                }}
              >
                <Trash2 size={15} aria-hidden="true" />
                Delete
              </Button>
            )}
            {onEdit && (
              <Button
                type="button"
                variant="secondary"
                onClick={() => {
                  onClose();
                  onEdit(note);
                }}
              >
                <Pencil size={15} aria-hidden="true" />
                Edit
              </Button>
            )}
            <Button type="button" variant="primary" onClick={onClose}>
              Done
            </Button>
          </div>
        </div>
      }
    >
      <div className="note-modal__meta">
        <div className="note-modal__associations">
          {hasProject && (
            <Link
              to={`/projects/${note.project_id}`}
              className="note-modal__badge-link"
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
              className="note-modal__badge-link"
            >
              <Badge variant="neutral" className="note-modal__task-badge">
                <CheckSquare size={13} aria-hidden="true" />
                <span>{note.task_title || `Task #${note.task_id}`}</span>
              </Badge>
            </Link>
          )}

          {!hasProject && !hasTask && (
            <span className="note-modal__general-badge">General Note</span>
          )}
        </div>

        <div className="note-modal__timestamps">
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

      <div className="note-modal__content">
        <RichTextViewer
          content={note.content}
          onCheckboxToggle={onCheckboxToggle}
          emptyMessage="No additional content in this note."
        />
      </div>
    </Modal>
  );
}

export default NoteModal;
