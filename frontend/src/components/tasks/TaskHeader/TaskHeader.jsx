import { Link } from "react-router-dom";
import { ChevronRight, Lock, Pencil, Sparkles, Trash2 } from "lucide-react";
import Button from "../../Button/Button.jsx";
import Badge from "../../Badge/Badge.jsx";
import "./TaskHeader.css";

function TaskHeader({
  projectId,
  projectName,
  taskTitle,
  isCompleted,
  isBlocked,
  onEdit,
  onDelete,
  onRegenerate,
}) {
  return (
    <div className="task-header">
      <nav className="task-header__breadcrumb" aria-label="Breadcrumb">
        <Link to="/projects">Projects</Link>
        <ChevronRight size={14} aria-hidden="true" />
        <Link to={`/projects/${projectId}`}>{projectName || "Project"}</Link>
        <ChevronRight size={14} aria-hidden="true" />
        <span className="task-header__breadcrumb-current" aria-current="page">
          {taskTitle}
        </span>
      </nav>

      <div className="task-header__top">
        <div className="task-header__title-group">
          <h1 className={`task-header__title ${isCompleted ? "task-header__title--completed" : ""}`}>
            {taskTitle}
          </h1>
          {isBlocked && (
            <Badge variant="danger" className="task-header__blocked-badge">
              <Lock size={12} aria-hidden="true" />
              Blocked
            </Badge>
          )}
        </div>
        <div className="task-header__actions">
          {onRegenerate && (
            <Button variant="secondary" onClick={onRegenerate}>
              <Sparkles size={16} aria-hidden="true" />
              Regenerate with AI
            </Button>
          )}
          <Button variant="secondary" onClick={onEdit}>
            <Pencil size={16} aria-hidden="true" />
            Edit
          </Button>
          <Button variant="danger" onClick={onDelete}>
            <Trash2 size={16} aria-hidden="true" />
            Delete
          </Button>
        </div>
      </div>
    </div>
  );
}

export default TaskHeader;