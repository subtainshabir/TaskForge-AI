import { useNavigate } from "react-router-dom";
import { CalendarClock, Pencil, Trash2 } from "lucide-react";
import Badge from "../../Badge/Badge.jsx";
import StatusSelect from "../StatusSelect/StatusSelect.jsx";
import { TASK_PRIORITY_META } from "../../../utils/taskPriority.js";
import { formatDueDate, isOverdue } from "../../../utils/date.js";
import "./TaskItem.css";

function TaskItem({ task, projectId, onStatusChange, onEdit, onDelete }) {
  const navigate = useNavigate();
  const { label: priorityLabel, icon: PriorityIcon, badgeVariant } = TASK_PRIORITY_META[task.priority];
  const dueLabel = formatDueDate(task.deadline);
  const overdue = isOverdue(task.deadline, task.status);

  function goToDetails() {
    navigate(`/projects/${projectId}/tasks/${task.id}`);
  }

  function handleKeyDown(event) {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      goToDetails();
    }
  }

  return (
    <div
      className="task-item"
      role="button"
      tabIndex={0}
      onClick={goToDetails}
      onKeyDown={handleKeyDown}
      aria-label={`Open ${task.title}`}
    >
      <div className="task-item__body">
        <h3 className="task-item__title">{task.title}</h3>
        {task.description && <p className="task-item__description">{task.description}</p>}
        <div className="task-item__meta">
          <StatusSelect
            value={task.status}
            onChange={(next) => onStatusChange(task, next)}
            label={`Status for ${task.title}`}
          />
          <Badge variant={badgeVariant} className="task-item__priority">
            <PriorityIcon size={12} aria-hidden="true" />
            {priorityLabel}
          </Badge>
          {dueLabel && (
            <span className={`task-item__due ${overdue ? "task-item__due--overdue" : ""}`}>
              <CalendarClock size={12} aria-hidden="true" />
              {overdue ? `Overdue · ${dueLabel}` : dueLabel}
            </span>
          )}
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