import { useEffect, useState } from "react";
import { AlertCircle, FolderKanban, CheckSquare } from "lucide-react";
import Input from "../../Input/Input.jsx";
import Textarea from "../../Textarea/Textarea.jsx";
import Button from "../../Button/Button.jsx";
import Badge from "../../Badge/Badge.jsx";
import { projectService } from "../../../services/projectService.js";
import { taskService } from "../../../services/taskService.js";
import "./NoteForm.css";

function NoteForm({
  initialValues = null,
  initialProjectId = null,
  initialTaskId = null,
  lockProject = false,
  lockTask = false,
  submitLabel = "Save Note",
  isSubmitting = false,
  apiError = "",
  onSubmit,
  onCancel,
}) {
  const isEdit = Boolean(initialValues?.id);

  const [title, setTitle] = useState(initialValues?.title || "");
  const [content, setContent] = useState(initialValues?.content || "");
  const [titleError, setTitleError] = useState("");

  const [projectId, setProjectId] = useState(
    initialValues?.project_id || initialProjectId || ""
  );
  const [taskId, setTaskId] = useState(
    initialValues?.task_id || initialTaskId || ""
  );

  const [projects, setProjects] = useState([]);
  const [projectTasks, setProjectTasks] = useState([]);
  const [isLoadingProjects, setIsLoadingProjects] = useState(false);
  const [isLoadingTasks, setIsLoadingTasks] = useState(false);

  // Load projects list if in create mode and project is not locked
  useEffect(() => {
    if (isEdit || lockProject) return;

    let isCurrent = true;
    setIsLoadingProjects(true);
    projectService
      .list()
      .then((data) => {
        if (isCurrent) setProjects(data || []);
      })
      .catch(() => {
        if (isCurrent) setProjects([]);
      })
      .finally(() => {
        if (isCurrent) setIsLoadingProjects(false);
      });

    return () => {
      isCurrent = false;
    };
  }, [isEdit, lockProject]);

  // Load tasks when project is selected/changed in create mode
  useEffect(() => {
    if (isEdit || lockTask) return;

    const currentProjId = projectId;
    if (!currentProjId) {
      setProjectTasks([]);
      setTaskId("");
      return;
    }

    let isCurrent = true;
    setIsLoadingTasks(true);
    taskService
      .list(currentProjId)
      .then((data) => {
        if (isCurrent) setProjectTasks(data || []);
      })
      .catch(() => {
        if (isCurrent) setProjectTasks([]);
      })
      .finally(() => {
        if (isCurrent) setIsLoadingTasks(false);
      });

    return () => {
      isCurrent = false;
    };
  }, [isEdit, projectId, lockTask]);

  function handleSubmit(event) {
    event.preventDefault();
    const trimmedTitle = title.trim();
    if (!trimmedTitle) {
      setTitleError("Note title is required.");
      return;
    }
    setTitleError("");

    if (isEdit) {
      onSubmit({
        title: trimmedTitle,
        content: content.trim() || null,
      });
    } else {
      onSubmit({
        title: trimmedTitle,
        content: content.trim() || null,
        project_id: projectId ? Number(projectId) : null,
        task_id: taskId ? Number(taskId) : null,
      });
    }
  }

  return (
    <form className="note-form" onSubmit={handleSubmit} noValidate>
      {apiError && (
        <div className="note-form__error" role="alert">
          <AlertCircle size={16} aria-hidden="true" />
          <span>{apiError}</span>
        </div>
      )}

      <Input
        label="Note title"
        value={title}
        onChange={(event) => {
          setTitle(event.target.value);
          setTitleError("");
        }}
        placeholder="e.g. Architecture decisions, meeting notes, ideas..."
        error={titleError}
        maxLength={255}
        autoFocus
        required
      />

      <Textarea
        label="Content"
        value={content}
        onChange={(event) => setContent(event.target.value)}
        placeholder="Write note details, checklists, references, or reminders..."
        rows={6}
        maxLength={50000}
        hint="Optional. Plain text is supported."
      />

      {isEdit ? (
        (initialValues?.project_name || initialValues?.task_title) && (
          <div className="note-form__associations-summary">
            <span className="note-form__assoc-label">Associations:</span>
            <div className="note-form__assoc-badges">
              {initialValues.project_name && (
                <Badge variant="neutral">
                  <FolderKanban size={12} aria-hidden="true" />
                  {initialValues.project_name}
                </Badge>
              )}
              {initialValues.task_title && (
                <Badge variant="neutral">
                  <CheckSquare size={12} aria-hidden="true" />
                  {initialValues.task_title}
                </Badge>
              )}
            </div>
          </div>
        )
      ) : (
        <div className="note-form__row">
          <div className="field">
            <label className="field__label" htmlFor="note-project-select">
              Project association
            </label>
            {lockProject ? (
              <div className="note-form__locked-assoc">
                <FolderKanban size={14} aria-hidden="true" />
                <span>
                  {initialValues?.project_name ||
                    projects.find((p) => p.id === Number(projectId))?.name ||
                    `Project #${projectId}`}
                </span>
              </div>
            ) : (
              <select
                id="note-project-select"
                className="field__control"
                value={projectId}
                disabled={isLoadingProjects}
                onChange={(e) => {
                  setProjectId(e.target.value);
                  setTaskId("");
                }}
              >
                <option value="">No Project (General Note)</option>
                {projects.map((proj) => (
                  <option key={proj.id} value={proj.id}>
                    {proj.name}
                  </option>
                ))}
              </select>
            )}
            <span className="field__hint">Optional project link</span>
          </div>

          <div className="field">
            <label className="field__label" htmlFor="note-task-select">
              Task association
            </label>
            {lockTask ? (
              <div className="note-form__locked-assoc">
                <CheckSquare size={14} aria-hidden="true" />
                <span>
                  {initialValues?.task_title ||
                    projectTasks.find((t) => t.id === Number(taskId))?.title ||
                    `Task #${taskId}`}
                </span>
              </div>
            ) : (
              <select
                id="note-task-select"
                className="field__control"
                value={taskId}
                disabled={!projectId || isLoadingTasks}
                onChange={(e) => setTaskId(e.target.value)}
              >
                <option value="">No Task (Project-level)</option>
                {projectTasks.map((t) => (
                  <option key={t.id} value={t.id}>
                    {t.title}
                  </option>
                ))}
              </select>
            )}
            <span className="field__hint">
              {!projectId && !lockTask
                ? "Select a project first to link a task"
                : "Optional task link"}
            </span>
          </div>
        </div>
      )}

      <div className="note-form__footer">
        <Button
          type="button"
          variant="ghost"
          onClick={onCancel}
          disabled={isSubmitting}
        >
          Cancel
        </Button>
        <Button type="submit" variant="primary" loading={isSubmitting}>
          {submitLabel}
        </Button>
      </div>
    </form>
  );
}

export default NoteForm;
