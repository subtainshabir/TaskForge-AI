import { useState } from "react";
import { AlertCircle } from "lucide-react";
import Input from "../../Input/Input.jsx";
import Textarea from "../../Textarea/Textarea.jsx";
import Button from "../../Button/Button.jsx";
import { TASK_STATUSES, TASK_STATUS_META } from "../../../utils/taskStatus.js";
import { TASK_PRIORITIES, TASK_PRIORITY_META } from "../../../utils/taskPriority.js";
import { toDateInputValue } from "../../../utils/date.js";
import "./TaskForm.css";

function TaskForm({ initialValues, submitLabel, isSubmitting, apiError, onSubmit, onCancel }) {
  const [title, setTitle] = useState(initialValues?.title || "");
  const [description, setDescription] = useState(initialValues?.description || "");
  const [status, setStatus] = useState(initialValues?.status || "todo");
  const [priority, setPriority] = useState(initialValues?.priority || "medium");
  const [dueDate, setDueDate] = useState(toDateInputValue(initialValues?.deadline));
  const [titleError, setTitleError] = useState("");

  function handleSubmit(event) {
    event.preventDefault();
    const trimmed = title.trim();
    if (!trimmed) {
      setTitleError("Task title is required.");
      return;
    }
    setTitleError("");
    onSubmit({
      title: trimmed,
      description: description.trim(),
      status,
      priority,
      deadline: dueDate ? new Date(`${dueDate}T00:00:00`).toISOString() : null,
    });
  }

  return (
    <form className="task-form" onSubmit={handleSubmit} noValidate>
      {apiError && (
        <div className="task-form__error" role="alert">
          <AlertCircle size={16} aria-hidden="true" />
          {apiError}
        </div>
      )}

      <Input
        label="Task title"
        value={title}
        onChange={(event) => {
          setTitle(event.target.value);
          setTitleError("");
        }}
        error={titleError}
        maxLength={255}
        autoFocus
      />

      <Textarea
        label="Description"
        value={description}
        onChange={(event) => setDescription(event.target.value)}
        rows={3}
        maxLength={5000}
        hint="Optional"
      />

      <div className="task-form__row">
        <div>
          <span className="task-form__label">Priority</span>
          <div className="task-form__options" role="group" aria-label="Task priority">
            {TASK_PRIORITIES.map((value) => {
              const { label, icon: Icon } = TASK_PRIORITY_META[value];
              return (
                <button
                  key={value}
                  type="button"
                  className="task-form__option"
                  aria-pressed={priority === value}
                  onClick={() => setPriority(value)}
                >
                  <Icon size={13} aria-hidden="true" />
                  {label}
                </button>
              );
            })}
          </div>
        </div>

        <Input
          type="date"
          label="Due date"
          value={dueDate}
          onChange={(event) => setDueDate(event.target.value)}
        />
      </div>

      <div>
        <span className="task-form__label">Status</span>
        <div className="task-form__options" role="group" aria-label="Task status">
          {TASK_STATUSES.map((value) => {
            const { label, icon: Icon } = TASK_STATUS_META[value];
            return (
              <button
                key={value}
                type="button"
                className="task-form__option"
                aria-pressed={status === value}
                onClick={() => setStatus(value)}
              >
                <Icon size={13} aria-hidden="true" />
                {label}
              </button>
            );
          })}
        </div>
      </div>

      <div className="task-form__footer">
        <Button type="button" variant="ghost" onClick={onCancel} disabled={isSubmitting}>
          Cancel
        </Button>
        <Button type="submit" variant="primary" loading={isSubmitting}>
          {submitLabel}
        </Button>
      </div>
    </form>
  );
}

export default TaskForm;