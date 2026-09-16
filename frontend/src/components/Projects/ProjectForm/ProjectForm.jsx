import { useState } from "react";
import { AlertCircle } from "lucide-react";
import Input from "../../Input/Input.jsx";
import Textarea from "../../Textarea/Textarea.jsx";
import Button from "../../Button/Button.jsx";
import { PROJECT_STATUSES, STATUS_META } from "../../../utils/projectStatus.js";
import "./ProjectForm.css";

function ProjectForm({ initialValues, submitLabel, isSubmitting, apiError, onSubmit, onCancel }) {
  const [name, setName] = useState(initialValues?.name || "");
  const [description, setDescription] = useState(initialValues?.description || "");
  const [status, setStatus] = useState(initialValues?.status || "active");
  const [nameError, setNameError] = useState("");

  function handleSubmit(event) {
    event.preventDefault();
    const trimmed = name.trim();
    if (!trimmed) {
      setNameError("Project name is required.");
      return;
    }
    setNameError("");
    onSubmit({ name: trimmed, description: description.trim(), status });
  }

  return (
    <form className="project-form" onSubmit={handleSubmit} noValidate>
      {apiError && (
        <div className="project-form__error" role="alert">
          <AlertCircle size={16} aria-hidden="true" />
          {apiError}
        </div>
      )}

      <Input
        label="Project name"
        value={name}
        onChange={(event) => {
          setName(event.target.value);
          setNameError("");
        }}
        error={nameError}
        maxLength={255}
        autoFocus
      />

      <Textarea
        label="Description"
        value={description}
        onChange={(event) => setDescription(event.target.value)}
        rows={4}
        maxLength={5000}
        hint="Optional"
      />

      <div>
        <span className="project-form__label">Status</span>
        <div className="project-form__status-options" role="group" aria-label="Project status">
          {PROJECT_STATUSES.map((value) => {
            const { label, icon: Icon } = STATUS_META[value];
            return (
              <button
                key={value}
                type="button"
                className="project-form__status-option"
                aria-pressed={status === value}
                onClick={() => setStatus(value)}
              >
                <Icon size={14} aria-hidden="true" />
                {label}
              </button>
            );
          })}
        </div>
      </div>

      <div className="project-form__footer">
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

export default ProjectForm;