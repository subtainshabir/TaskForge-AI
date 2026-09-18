import { useEffect, useState } from "react";
import StatusSelect from "../StatusSelect/StatusSelect.jsx";
import { taskService } from "../../../services/taskService.js";
import { apiErrorMessage } from "../../../utils/apiErrorMessage.js";
import "./TaskControls.css";

function TaskStatusControl({ task, onUpdated }) {
  const [localStatus, setLocalStatus] = useState(task.status);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    setLocalStatus(task.status);
  }, [task.status]);

  async function handleChange(nextStatus) {
    if (nextStatus === localStatus) return;
    const previous = localStatus;
    setLocalStatus(nextStatus);
    setIsSaving(true);
    setError("");
    try {
      const updated = await taskService.update(task.id, { status: nextStatus });
      setLocalStatus(updated.status);
      onUpdated(updated);
    } catch (err) {
      setLocalStatus(previous);
      setError(apiErrorMessage(err));
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <div className="task-control">
      <span className="task-control__label">Status</span>
      <StatusSelect
        value={localStatus}
        onChange={handleChange}
        disabled={isSaving}
        label="Task status"
      />
      {error && <span className="task-control__error">{error}</span>}
    </div>
  );
}

export default TaskStatusControl;