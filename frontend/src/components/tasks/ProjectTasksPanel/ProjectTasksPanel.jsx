import { useMemo, useState } from "react";
import { CheckSquare, Plus, SearchX } from "lucide-react";
import Card from "../../Card/Card.jsx";
import Button from "../../Button/Button.jsx";
import Modal from "../../Modal/Modal.jsx";
import { EmptyState, ErrorState } from "../../StatePanel/StatePanel.jsx";
import TaskFilters from "../TaskFilters/TaskFilters.jsx";
import TaskList from "../TaskList/Tasklist.jsx";
import TaskForm from "../TaskForm/TaskForm.jsx";
import DeleteTaskDialog from "../DeleteTaskDialog/DeleteTaskDialog.jsx";
import { useTasks } from "../../../hooks/useTasks.js";
import { taskService } from "../../../services/taskService.js";
import { apiErrorMessage } from "../../../utils/apiErrorMessage.js";
import "./ProjectTasksPanel.css";

function ProjectTasksPanel({ projectId }) {
  const { tasks, isLoading, error, refetch, addTask, replaceTask, removeTask } =
    useTasks(projectId);

  const [statusFilter, setStatusFilter] = useState("");
  const [search, setSearch] = useState("");

  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [editingTask, setEditingTask] = useState(null);
  const [deletingTask, setDeletingTask] = useState(null);

  const [isSaving, setIsSaving] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [formError, setFormError] = useState("");
  const [deleteError, setDeleteError] = useState("");
  const [quickUpdateError, setQuickUpdateError] = useState("");

  const filteredTasks = useMemo(() => {
    const query = search.trim().toLowerCase();
    return tasks.filter((task) => {
      const matchesStatus = !statusFilter || task.status === statusFilter;
      const matchesSearch =
        !query ||
        task.title.toLowerCase().includes(query) ||
        (task.description || "").toLowerCase().includes(query);
      return matchesStatus && matchesSearch;
    });
  }, [tasks, statusFilter, search]);

  const hasAnyTasks = tasks.length > 0;
  const hasActiveFilters = Boolean(statusFilter || search.trim());

  async function handleCreate(payload) {
    setIsSaving(true);
    setFormError("");
    try {
      const created = await taskService.create(projectId, payload);
      addTask(created);
      setIsCreateOpen(false);
    } catch (err) {
      setFormError(apiErrorMessage(err));
    } finally {
      setIsSaving(false);
    }
  }

  async function handleUpdate(payload) {
    if (!editingTask) return;
    setIsSaving(true);
    setFormError("");
    try {
      const updated = await taskService.update(editingTask.id, payload);
      replaceTask(updated);
      setEditingTask(null);
    } catch (err) {
      setFormError(apiErrorMessage(err, "This task no longer exists."));
    } finally {
      setIsSaving(false);
    }
  }

  async function handleStatusChange(task, nextStatus) {
    const previous = task.status;
    replaceTask({ ...task, status: nextStatus });
    setQuickUpdateError("");
    try {
      const updated = await taskService.update(task.id, { status: nextStatus });
      replaceTask(updated);
    } catch (err) {
      replaceTask({ ...task, status: previous });
      setQuickUpdateError(apiErrorMessage(err, "Unable to update task status. Please try again."));
    }
  }

  async function handlePriorityChange(task, nextPriority) {
    const previous = task.priority;
    replaceTask({ ...task, priority: nextPriority });
    setQuickUpdateError("");
    try {
      const updated = await taskService.update(task.id, { priority: nextPriority });
      replaceTask(updated);
    } catch (err) {
      replaceTask({ ...task, priority: previous });
      setQuickUpdateError(apiErrorMessage(err, "Unable to update task priority. Please try again."));
    }
  }

  async function handleToggleComplete(task) {
    const previous = task.status;
    const nextStatus = task.status === "completed" ? "todo" : "completed";
    replaceTask({ ...task, status: nextStatus });
    setQuickUpdateError("");
    try {
      const updated = await taskService.update(task.id, { status: nextStatus });
      replaceTask(updated);
    } catch (err) {
      replaceTask({ ...task, status: previous });
      setQuickUpdateError(apiErrorMessage(err, "Unable to update task status. Please try again."));
    }
  }

  async function handleDelete() {
    if (!deletingTask) return;
    setIsDeleting(true);
    setDeleteError("");
    try {
      await taskService.remove(deletingTask.id);
      removeTask(deletingTask.id);
      setDeletingTask(null);
    } catch (err) {
      setDeleteError(apiErrorMessage(err, "This task no longer exists."));
    } finally {
      setIsDeleting(false);
    }
  }

  return (
    <div>
      <div className="project-tasks-panel__header">
        <h2 style={{ margin: 0 }}>Tasks</h2>
        <Button variant="primary" onClick={() => setIsCreateOpen(true)}>
          <Plus size={16} aria-hidden="true" />
          New Task
        </Button>
      </div>

      {hasAnyTasks && (
        <TaskFilters
          status={statusFilter}
          onStatusChange={setStatusFilter}
          search={search}
          onSearchChange={setSearch}
        />
      )}

      {quickUpdateError && (
        <div
          role="alert"
          style={{
            marginBottom: "var(--space-4)",
            padding: "var(--space-3)",
            borderRadius: "var(--radius-md)",
            background: "var(--color-danger-soft)",
            color: "var(--color-danger)",
            fontSize: "var(--text-sm)",
          }}
        >
          {quickUpdateError}
        </div>
      )}

      {error && !isLoading && (
        <Card>
          <ErrorState
            title="Couldn't load tasks"
            description={error}
            action={
              <Button variant="secondary" onClick={refetch}>
                Try again
              </Button>
            }
          />
        </Card>
      )}

      {!error && isLoading && <TaskList tasks={[]} isLoading projectId={projectId} />}

      {!error && !isLoading && !hasAnyTasks && (
        <Card className="project-tasks-panel__empty-card">
          <EmptyState
            icon={<CheckSquare size={22} aria-hidden="true" />}
            title="No tasks yet"
            description="Break your project into actionable work and start making progress."
            action={
              <Button variant="primary" onClick={() => setIsCreateOpen(true)}>
                <Plus size={16} aria-hidden="true" />
                Create Task
              </Button>
            }
          />
        </Card>
      )}

      {!error && !isLoading && hasAnyTasks && filteredTasks.length === 0 && (
        <Card className="project-tasks-panel__empty-card">
          <EmptyState
            icon={<SearchX size={22} aria-hidden="true" />}
            title="No tasks match your filters"
            description="Try a different search term or clear the current filters."
            action={
              hasActiveFilters && (
                <Button
                  variant="secondary"
                  onClick={() => {
                    setStatusFilter("");
                    setSearch("");
                  }}
                >
                  Clear filters
                </Button>
              )
            }
          />
        </Card>
      )}

      {!error && !isLoading && filteredTasks.length > 0 && (
        <TaskList
          tasks={filteredTasks}
          isLoading={false}
          projectId={projectId}
          onStatusChange={handleStatusChange}
          onPriorityChange={handlePriorityChange}
          onToggleComplete={handleToggleComplete}
          onEdit={setEditingTask}
          onDelete={setDeletingTask}
        />
      )}

      <Modal
        open={isCreateOpen}
        onClose={() => {
          setIsCreateOpen(false);
          setFormError("");
        }}
        title="New task"
      >
        <TaskForm
          submitLabel="Create task"
          isSubmitting={isSaving}
          apiError={formError}
          onSubmit={handleCreate}
          onCancel={() => {
            setIsCreateOpen(false);
            setFormError("");
          }}
        />
      </Modal>

      <Modal
        open={Boolean(editingTask)}
        onClose={() => {
          setEditingTask(null);
          setFormError("");
        }}
        title="Edit task"
      >
        {editingTask && (
          <TaskForm
            initialValues={editingTask}
            submitLabel="Save changes"
            isSubmitting={isSaving}
            apiError={formError}
            onSubmit={handleUpdate}
            onCancel={() => {
              setEditingTask(null);
              setFormError("");
            }}
          />
        )}
      </Modal>

      <DeleteTaskDialog
        task={deletingTask}
        open={Boolean(deletingTask)}
        isDeleting={isDeleting}
        apiError={deleteError}
        onConfirm={handleDelete}
        onCancel={() => {
          setDeletingTask(null);
          setDeleteError("");
        }}
      />
    </div>
  );
}

export default ProjectTasksPanel;