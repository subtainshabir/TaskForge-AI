import { useNavigate } from "react-router-dom";
import { Pencil, Trash2 } from "lucide-react";
import Card from "../../Card/Card.jsx";
import Badge from "../../Badge/Badge.jsx";
import { STATUS_META } from "../../../utils/projectStatus.js";
import { formatRelativeDate } from "../../../utils/date.js";
import "./ProjectCard.css";

function ProjectCard({ project, onEdit, onDelete }) {
  const navigate = useNavigate();
  const { label, icon: Icon, badgeVariant } = STATUS_META[project.status];

  function goToDetails() {
    navigate(`/projects/${project.id}`);
  }

  function handleKeyDown(event) {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      goToDetails();
    }
  }

  return (
    <Card
      className="project-card"
      interactive
      role="button"
      onClick={goToDetails}
      onKeyDown={handleKeyDown}
      aria-label={`Open ${project.name}`}
    >
      <div className="project-card__header">
        <h3 className="project-card__name">{project.name}</h3>
        <div className="project-card__actions">
          <button
            type="button"
            className="project-card__action"
            aria-label={`Edit ${project.name}`}
            onClick={(event) => {
              event.stopPropagation();
              onEdit(project);
            }}
          >
            <Pencil size={15} aria-hidden="true" />
          </button>
          <button
            type="button"
            className="project-card__action project-card__action--danger"
            aria-label={`Delete ${project.name}`}
            onClick={(event) => {
              event.stopPropagation();
              onDelete(project);
            }}
          >
            <Trash2 size={15} aria-hidden="true" />
          </button>
        </div>
      </div>

      <p className="project-card__description">
        {project.description || "No description provided."}
      </p>

      <div className="project-card__footer">
        <Badge variant={badgeVariant} className="project-card__badge">
          <Icon size={12} aria-hidden="true" />
          {label}
        </Badge>
        <span className="project-card__updated">Updated {formatRelativeDate(project.updated_at)}</span>
      </div>
    </Card>
  );
}

export default ProjectCard;