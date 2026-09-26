import { useMemo, useState } from "react";
import { CheckSquare, Plus, SearchX, Sparkles } from "lucide-react";
import Card from "../../Card/Card.jsx";
import Button from "../../Button/Button.jsx";
import Modal from "../../Modal/Modal.jsx";
import { EmptyState, ErrorState } from "../../StatePanel/StatePanel.jsx";
import TaskFilters from "../TaskFilters/TaskFilters.jsx";
import TaskSort from "../TaskSort/TaskSort.jsx";
import ActiveFilters from "../ActiveFilters/ActiveFilters.jsx";
import TaskList from "../TaskList/TaskList.jsx";
import TaskForm from "../TaskForm/TaskForm.jsx";
import DeleteTaskDialog from "../DeleteTaskDialog/DeleteTaskDialog.jsx";
import TaskAISuggestions from "../TaskAISuggestions/TaskAISuggestions.jsx";
import { useTasks } from "../../../hooks/useTasks.js";
import { useTaskFilters } from "../../../hooks/useTaskFilters.js";
import { useDebouncedValue } from "../../../hooks/useDebouncedValue.js";
import { taskService } from "../../../services/taskService.js";
import { apiErrorMessage } from "../../../utils/apiErrorMessage.js";
import { filterTasks, sortTasks } from "../../../utils/taskFilterSort.js";
import "./ProjectTasksPanel.css";

function ProjectTasksPanel({ projectId }) {
  const {
    status,
    priority,
    due,
    search,
    sortBy,
    order,
    setStatus,
    setPriority,
    setDue,
    setSearch,
    setSort,
    toggleOrder,
    clearFilters,
    hasActiveFilters,
  } = useTaskFilters();

  const debouncedSearch = useDebouncedValue(search, 350);
  const isSearchActive = Boolean(debouncedSearch.trim());
  const hasClientFilters = Boolean(status || priority || due);

  const { tasks, isLoading, error, refetch, addTask, replaceTask, removeTask } = useTasks(
    projectId,
    debouncedSearch
  );

  const isSearching = isSearchActive && isLoading;

  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [isSuggestionsOpen, setIsSuggestionsOpen] = useState(false);
  const [editingTask, setEditingTask] = useState(null);
  const [deletingTask, setDeletingTask] = useState(null);

  const [isSaving, setIsSaving] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [formError, setFormError] = useState("");
  const [deleteError, setDeleteError] = useState("");
  const [quickUpdateError, setQuickUpdateError] = useState("");

  const visibleTasks = useMemo(() => {
    const filtered = filterTasks(tasks, { status, priority, due });
    return sortTasks(filtered, sortBy, order);
  }, [tasks, status, priority, due, sortBy, order]);

  const showNoTasksYet = !isSearchActive && tasks.length === 0;
  const showNoSearchResults = isSearchActive && tasks.length === 0;
  const showNoFilterResults = tasks.length > 0 && visibleTasks.length === 0;

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

  function countLabel() {
    if (isSearchActive) return `${visibleTasks.length} tasks found`;
    if (hasClientFilters) return `Showing ${visibleTasks.length} of ${tasks.length} tasks`;
    return `${tasks.length} tasks`;
  }

  const showToolbar = tasks.length > 0 || isSearchActive || hasClientFilters;

  return (
    <div>
      <div className="project-tasks-panel__header">
        <h2 style={{ margin: 0 }}>Tasks</h2>
        <div style={{ display: "flex", gap: "var(--space-2)", alignItems: "center" }}>
          <Button
            variant="secondary"
            onClick={() => setIsSuggestionsOpen((prev) => !prev)}
            aria-expanded={isSuggestionsOpen}
          >
            <Sparkles size={16} aria-hidden="true" />
            Suggest Tasks with AI
          </Button>
          <Button variant="primary" onClick={() => setIsCreateOpen(true)}>
            <Plus size={16} aria-hidden="true" />
            New Task
          </Button>
        </div>
      </div>

      {isSuggestionsOpen && (
        <TaskAISuggestions
          projectId={projectId}
          autoFetch
          showCloseButton
          onClose={() => setIsSuggestionsOpen(false)}
          onTasksCreated={(createdList) => {
            createdList.forEach((t) => addTask(t));
          }}
        />
      )}

      {showToolbar && (
        <>
          <div style={{ display: "flex", flexWrap: "wrap", gap: "var(--space-2)", alignItems: "center" }}>
            <div style={{ flex: 1, minWidth: 0 }}>
              <TaskFilters
                status={status}
                onStatusChange={setStatus}
                priority={priority}
                onPriorityChange={setPriority}
                due={due}
                onDueChange={setDue}
                search={search}
                onSearchChange={setSearch}
                isSearching={isSearching}
              />
            </div>
            <TaskSort sortBy={sortBy} order={order} onSortChange={setSort} onToggleOrder={toggleOrder} />
          </div>

          <ActiveFilters
            status={status}
            priority={priority}
            due={due}
            search={search}
            onClearStatus={() => setStatus("")}
            onClearPriority={() => setPriority("")}
            onClearDue={() => setDue("")}
            onClearSearch={() => setSearch("")}
            onClearAll={clearFilters}
          />

          {!isLoading && !error && <p className="task-count">{countLabel()}</p>}
        </>
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

      {!error && !isLoading && showNoTasksYet && (
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

      {!error && !isLoading && showNoSearchResults && (
        <Card className="project-tasks-panel__empty-card">
          <EmptyState
            icon={<SearchX size={22} aria-hidden="true" />}
            title="No tasks found"
            description={`No tasks match "${debouncedSearch.trim()}". Try a different search term.`}
            action={
              <Button variant="secondary" onClick={() => setSearch("")}>
                Clear search
              </Button>
            }
          />
        </Card>
      )}

      {!error && !isLoading && !showNoSearchResults && showNoFilterResults && (
        <Card className="project-tasks-panel__empty-card">
          <EmptyState
            icon={<SearchX size={22} aria-hidden="true" />}
            title="No tasks match these filters"
            description="Try changing or clearing your filters."
            action={
              <Button variant="secondary" onClick={clearFilters}>
                Clear filters
              </Button>
            }
          />
        </Card>
      )}

      {!error && !isLoading && visibleTasks.length > 0 && (
        <TaskList
          tasks={visibleTasks}
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