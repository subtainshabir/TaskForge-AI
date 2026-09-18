import { useState } from "react";
import { CalendarClock } from "lucide-react";
import { taskService } from "../../../services/taskService.js";
import { apiErrorMessage } from "../../../utils/apiErrorMessage.js";
import { formatDueDate, isOverdue, toDateInputValue } from "../../../utils/date.js";
import "../TaskStatusControl/TaskControls.css";

function TaskDueDateControl({ task, onUpdated }) {
  const [isEditing, setIsEditing] = useState(false);
  const [draft, setDraft] = useState(toDateInputValue(task.deadline));
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState("");

  const dueLabel = formatDueDate(task.deadline);
  const overdue = isOverdue(task.deadline, task.status);

  async function save(nextDeadline) {
    setIsSaving(true);
    setError("");
    try {
      const updated = await taskService.update(task.id, { deadline: nextDeadline });
      onUpdated(updated);
      setIsEditing(false);
    } catch (err) {
      setError(apiErrorMessage(err));
    } finally {
      setIsSaving(false);
    }
  }

  function handleSave() {
    const nextDeadline = draft ? new Date(`${draft}T00:00:00`).toISOString() : null;
    save(nextDeadline);
  }

  if (isEditing) {
    return (
      <div className="task-control">
        <span className="task-control__label">Due date</span>
        <div className="task-control__due-editing">
          <input
            type="date"
            value={draft}
            disabled={isSaving}
            onChange={(event) => setDraft(event.target.value)}
            aria-label="Due date"
          />
          <button type="button" className="task-control__due-clear" onClick={handleSave} disabled={isSaving}>
            {isSaving ? "Saving…" : "Save"}
          </button>
          <button
            type="button"
            className="task-control__due-clear"
            onClick={() => {
              setDraft("");
              setIsEditing(false);
            }}
            disabled={isSaving}
          >
            Cancel
          </button>
        </div>
        {task.deadline && (
          <button
            type="button"
            className="task-control__due-clear"
            onClick={() => save(null)}
            disabled={isSaving}
          >
            Remove due date
          </button>
        )}
        {error && <span className="task-control__error">{error}</span>}
      </div>
    );
  }

  return (
    <div className="task-control">
      <span className="task-control__label">Due date</span>
      <button
        type="button"
        className={`task-control__due-button ${overdue ? "task-control__due-button--overdue" : ""}`}
        onClick={() => {
          setDraft(toDateInputValue(task.deadline));
          setIsEditing(true);
        }}
      >
        <CalendarClock size={12} aria-hidden="true" />
        {dueLabel ? (overdue ? `Overdue · ${dueLabel}` : dueLabel) : "Set due date"}
      </button>
      {error && <span className="task-control__error">{error}</span>}
    </div>
  );
}

export default TaskDueDateControl;