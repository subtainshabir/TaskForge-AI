import { useEffect, useState } from "react";
import PrioritySelect from "./PrioritySelect.jsx";
import { taskService } from "../../../services/taskService.js";
import { apiErrorMessage } from "../../../utils/apiErrorMessage.js";
import "../TaskStatusControl/TaskControls.css";

function TaskPriorityControl({ task, onUpdated }) {
  const [localPriority, setLocalPriority] = useState(task.priority);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    setLocalPriority(task.priority);
  }, [task.priority]);

  async function handleChange(nextPriority) {
    if (nextPriority === localPriority) return;
    const previous = localPriority;
    setLocalPriority(nextPriority);
    setIsSaving(true);
    setError("");
    try {
      const updated = await taskService.update(task.id, { priority: nextPriority });
      setLocalPriority(updated.priority);
      onUpdated(updated);
    } catch (err) {
      setLocalPriority(previous);
      setError(apiErrorMessage(err));
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <div className="task-control">
      <span className="task-control__label">Priority</span>
      <PrioritySelect
        value={localPriority}
        onChange={handleChange}
        disabled={isSaving}
        label="Task priority"
      />
      {error && <span className="task-control__error">{error}</span>}
    </div>
  );
}

export default TaskPriorityControl;