import { useCallback, useEffect, useMemo, useState } from "react";
import {
  AlertCircle,
  Check,
  CheckCircle2,
  Circle,
  Lock,
  PauseCircle,
  PlayCircle,
  Plus,
  Trash2,
  XCircle,
} from "lucide-react";
import Card from "../../Card/Card.jsx";
import Button from "../../Button/Button.jsx";
import Badge from "../../Badge/Badge.jsx";
import Modal from "../../Modal/Modal.jsx";
import Spinner from "../../Spinner/Spinner.jsx";
import { taskService } from "../../../services/taskService.js";
import { apiErrorMessage } from "../../../utils/apiErrorMessage.js";
import { TASK_STATUS_META } from "../../../utils/taskStatus.js";
import "./TaskDependencies.css";

const STATUS_ICONS = {
  todo: Circle,
  in_progress: PlayCircle,
  blocked: PauseCircle,
  completed: CheckCircle2,
  cancelled: XCircle,
};

function TaskDependencies({ taskId, projectId, onBlockedChange, onDependencyChange }) {
  const [dependencies, setDependencies] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");

  const [isAddOpen, setIsAddOpen] = useState(false);
  const [projectTasks, setProjectTasks] = useState([]);
  const [isLoadingTasks, setIsLoadingTasks] = useState(false);
  const [selectedTaskId, setSelectedTaskId] = useState("");
  const [isAdding, setIsAdding] = useState(false);
  const [addError, setAddError] = useState("");

  const [deletingId, setDeletingId] = useState(null);
  const [actionError, setActionError] = useState("");

  const fetchDependencies = useCallback(async () => {
    setIsLoading(true);
    setError("");
    try {
      const data = await taskService.getDependencies(taskId);
      setDependencies(data || []);
    } catch (err) {
      setError(apiErrorMessage(err, "Failed to load dependencies."));
    } finally {
      setIsLoading(false);
    }
  }, [taskId]);

  useEffect(() => {
    fetchDependencies();
  }, [fetchDependencies]);

  const isBlocked = useMemo(() => {
    if (!dependencies || dependencies.length === 0) return false;
    return dependencies.some(
      (dep) =>
        dep.dependency_task &&
        dep.dependency_task.status !== "completed" &&
        dep.dependency_task.status !== "cancelled"
    );
  }, [dependencies]);

  useEffect(() => {
    onBlockedChange?.(isBlocked);
  }, [isBlocked, onBlockedChange]);

  const openAddModal = async () => {
    setIsAddOpen(true);
    setSelectedTaskId("");
    setAddError("");
    setIsLoadingTasks(true);
    try {
      const tasks = await taskService.list(projectId);
      setProjectTasks(tasks || []);
    } catch (err) {
      setAddError(apiErrorMessage(err, "Failed to load project tasks."));
    } finally {
      setIsLoadingTasks(false);
    }
  };

  const closeAddModal = () => {
    setIsAddOpen(false);
    setSelectedTaskId("");
    setAddError("");
  };

  const availableTasks = useMemo(() => {
    const depTaskIds = new Set(dependencies.map((d) => d.depends_on_task_id));
    return projectTasks.filter(
      (t) => t.id !== Number(taskId) && !depTaskIds.has(t.id)
    );
  }, [projectTasks, dependencies, taskId]);

  const handleAddDependency = async (e) => {
    e?.preventDefault();
    if (!selectedTaskId) {
      setAddError("Please select a task to depend on.");
      return;
    }
    setIsAdding(true);
    setAddError("");
    try {
      const created = await taskService.addDependency(taskId, Number(selectedTaskId));
      setDependencies((prev) => [...prev, created]);
      closeAddModal();
      onDependencyChange?.();
    } catch (err) {
      setAddError(apiErrorMessage(err, "Failed to add dependency."));
    } finally {
      setIsAdding(false);
    }
  };

  const handleRemoveDependency = async (dependencyId) => {
    setDeletingId(dependencyId);
    setActionError("");
    try {
      await taskService.removeDependency(taskId, dependencyId);
      setDependencies((prev) => prev.filter((d) => d.id !== dependencyId));
      onDependencyChange?.();
    } catch (err) {
      setActionError(apiErrorMessage(err, "Failed to remove dependency."));
    } finally {
      setDeletingId(null);
    }
  };

  return (
    <Card className="task-dependencies">
      <div className="task-dependencies__header">
        <div className="task-dependencies__title-wrap">
          <h2 className="task-details__section-title" style={{ margin: 0 }}>
            Dependencies
          </h2>
          {isBlocked ? (
            <Badge variant="danger" className="task-dependencies__badge">
              <Lock size={12} aria-hidden="true" />
              Blocked
            </Badge>
          ) : dependencies.length > 0 ? (
            <Badge variant="success" className="task-dependencies__badge">
              <Check size={12} aria-hidden="true" />
              Not blocked
            </Badge>
          ) : null}
        </div>
        <Button variant="secondary" size="sm" onClick={openAddModal}>
          <Plus size={15} aria-hidden="true" />
          Add dependency
        </Button>
      </div>

      <p className="task-dependencies__subheading">Blocked by</p>

      {actionError && (
        <div className="task-dependencies__error" role="alert">
          <AlertCircle size={15} aria-hidden="true" />
          <span>{actionError}</span>
        </div>
      )}

      {isLoading ? (
        <div className="task-dependencies__loading">
          <Spinner size="sm" />
          <span>Loading dependencies...</span>
        </div>
      ) : error ? (
        <div className="task-dependencies__error" role="alert">
          <AlertCircle size={15} aria-hidden="true" />
          <span>{error}</span>
        </div>
      ) : dependencies.length === 0 ? (
        <p className="task-dependencies__empty">
          No dependencies yet. This task is not waiting on any other tasks.
        </p>
      ) : (
        <div className="task-dependencies__list">
          {dependencies.map((dep) => {
            const task = dep.dependency_task;
            const statusKey = task?.status || "todo";
            const meta =
              TASK_STATUS_META[statusKey] || {
                label: statusKey,
                badgeVariant: "neutral",
              };
            const StatusIcon = STATUS_ICONS[statusKey] || Circle;
            const isDeleting = deletingId === dep.id;

            return (
              <div key={dep.id} className="task-dependency-item">
                <div className="task-dependency-item__info">
                  <div className="task-dependency-item__title-row">
                    <StatusIcon
                      size={16}
                      className={`task-dependency-item__status-icon task-dependency-item__status-icon--${meta.badgeVariant}`}
                      aria-hidden="true"
                    />
                    <span className="task-dependency-item__title">
                      {task?.title || `Task #${dep.depends_on_task_id}`}
                    </span>
                  </div>
                  <div className="task-dependency-item__meta">
                    <Badge variant={meta.badgeVariant}>{meta.label}</Badge>
                  </div>
                </div>

                <button
                  type="button"
                  className="task-dependency-item__remove"
                  aria-label={`Remove dependency on ${task?.title || "task"}`}
                  disabled={isDeleting}
                  onClick={() => handleRemoveDependency(dep.id)}
                  title="Remove dependency"
                >
                  <Trash2 size={15} aria-hidden="true" />
                </button>
              </div>
            );
          })}
        </div>
      )}

      <Modal
        open={isAddOpen}
        onClose={closeAddModal}
        title="Add dependency"
        footer={
          <>
            <Button
              type="button"
              variant="ghost"
              onClick={closeAddModal}
              disabled={isAdding}
            >
              Cancel
            </Button>
            <Button
              type="button"
              variant="primary"
              loading={isAdding}
              disabled={isAdding || !selectedTaskId || availableTasks.length === 0}
              onClick={handleAddDependency}
            >
              Add dependency
            </Button>
          </>
        }
      >
        <form onSubmit={handleAddDependency}>
          {addError && (
            <div className="task-dependencies__modal-error" role="alert">
              <AlertCircle size={15} aria-hidden="true" />
              <span>{addError}</span>
            </div>
          )}

          {isLoadingTasks ? (
            <div className="task-dependencies__modal-loading">
              <Spinner size="sm" />
              <span>Loading project tasks...</span>
            </div>
          ) : availableTasks.length === 0 ? (
            <p className="task-dependencies__empty">
              No available tasks in this project to add as dependency.
            </p>
          ) : (
            <div className="field">
              <label className="field__label" htmlFor="dependency-task-select">
                Select prerequisite task
              </label>
              <select
                id="dependency-task-select"
                className="field__control"
                value={selectedTaskId}
                onChange={(e) => setSelectedTaskId(e.target.value)}
                disabled={isAdding}
              >
                <option value="">-- Choose a task --</option>
                {availableTasks.map((t) => (
                  <option key={t.id} value={t.id}>
                    {t.title} ({TASK_STATUS_META[t.status]?.label || t.status})
                  </option>
                ))}
              </select>
              <span className="field__hint">
                This task will logically wait until the selected task is completed.
              </span>
            </div>
          )}
        </form>
      </Modal>
    </Card>
  );
}

export default TaskDependencies;
