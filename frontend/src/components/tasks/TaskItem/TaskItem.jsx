import { Link, useNavigate } from "react-router-dom";
import { CalendarClock, FolderKanban, Lock, Pencil, Trash2 } from "lucide-react";
import StatusSelect from "../StatusSelect/StatusSelect.jsx";
import PrioritySelect from "../TaskPriorityControl/PrioritySelect.jsx";
import { getDueDateInfo } from "../../../utils/date.js";
import "./TaskItem.css";

function TaskItem({
  task,
  projectId,
  showProject = !projectId,
  onStatusChange,
  onPriorityChange,
  onToggleComplete,
  onEdit,
  onDelete,
}) {
  const navigate = useNavigate();
  const targetProjectId = projectId || task.project_id;
  const dueInfo = getDueDateInfo(task.deadline, task.status);
  const isCompleted = task.status === "completed";
  const isCancelled = task.status === "cancelled";

  function goToDetails() {
    navigate(`/projects/${targetProjectId}/tasks/${task.id}`);
  }

  function handleKeyDown(event) {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      goToDetails();
    }
  }

  const itemClass = [
    "task-item",
    isCompleted && "task-item--completed",
    isCancelled && "task-item--cancelled",
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <div
      className={itemClass}
      role="button"
      tabIndex={0}
      onClick={goToDetails}
      onKeyDown={handleKeyDown}
      aria-label={`Open ${task.title}`}
    >
      <input
        type="checkbox"
        className="task-item__checkbox"
        checked={isCompleted}
        aria-label={isCompleted ? `Mark ${task.title} as todo` : `Mark ${task.title} as complete`}
        onClick={(event) => event.stopPropagation()}
        onChange={() => onToggleComplete(task)}
      />

      <div className="task-item__body">
        <h3 className="task-item__title">{task.title}</h3>
        {showProject && task.project_name && (
          <div className="task-item__project">
            <Link
              to={`/projects/${targetProjectId}`}
              className="task-item__project-link"
              onClick={(event) => event.stopPropagation()}
              title={`Open project: ${task.project_name}`}
            >
              <FolderKanban size={13} aria-hidden="true" />
              <span>{task.project_name}</span>
            </Link>
          </div>
        )}
        {task.description && <p className="task-item__description">{task.description}</p>}
        <div className="task-item__meta">
          <StatusSelect
            value={task.status}
            onChange={(next) => onStatusChange(task, next)}
            label={`Status for ${task.title}`}
          />
          <PrioritySelect
            value={task.priority}
            onChange={(next) => onPriorityChange(task, next)}
            label={`Priority for ${task.title}`}
          />
          {task.is_blocked && (
            <span className="task-item__blocked" title="Blocked by prerequisite tasks">
              <Lock size={12} aria-hidden="true" />
              Blocked
            </span>
          )}
          <span className={`task-item__due task-item__due--${dueInfo.urgency}`}>
            {dueInfo.urgency !== "none" && <CalendarClock size={12} aria-hidden="true" />}
            {dueInfo.label}
          </span>
        </div>
      </div>

      <div className="task-item__actions">
        <button
          type="button"
          className="task-item__action"
          aria-label={`Edit ${task.title}`}
          onClick={(event) => {
            event.stopPropagation();
            onEdit(task);
          }}
        >
          <Pencil size={15} aria-hidden="true" />
        </button>
        <button
          type="button"
          className="task-item__action task-item__action--danger"
          aria-label={`Delete ${task.title}`}
          onClick={(event) => {
            event.stopPropagation();
            onDelete(task);
          }}
        >
          <Trash2 size={15} aria-hidden="true" />
        </button>
      </div>
    </div>
  );
}

export default TaskItem;