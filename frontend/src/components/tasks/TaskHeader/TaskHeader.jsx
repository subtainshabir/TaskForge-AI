import { Link } from "react-router-dom";
import { ChevronRight, Pencil, Trash2 } from "lucide-react";
import Button from "../../Button/Button.jsx";
import "./TaskHeader.css";

function TaskHeader({ projectId, projectName, taskTitle, onEdit, onDelete }) {
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
        <h1 className="task-header__title">{taskTitle}</h1>
        <div className="task-header__actions">
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