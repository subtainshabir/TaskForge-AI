import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { CheckSquare, FolderKanban, SearchX } from "lucide-react";
import PageContainer from "../../components/PageContainer/PageContainer.jsx";
import Card from "../../components/Card/Card.jsx";
import Button from "../../components/Button/Button.jsx";
import Modal from "../../components/Modal/Modal.jsx";
import { EmptyState, ErrorState } from "../../components/StatePanel/StatePanel.jsx";
import TaskFilters from "../../components/tasks/TaskFilters/TaskFilters.jsx";
import TaskSort from "../../components/tasks/TaskSort/TaskSort.jsx";
import ActiveFilters from "../../components/tasks/ActiveFilters/ActiveFilters.jsx";
import TaskList from "../../components/tasks/TaskList/TaskList.jsx";
import TaskForm from "../../components/tasks/TaskForm/TaskForm.jsx";
import DeleteTaskDialog from "../../components/tasks/DeleteTaskDialog/DeleteTaskDialog.jsx";
import { useTasks } from "../../hooks/useTasks.js";
import { useTaskFilters } from "../../hooks/useTaskFilters.js";
import { useDebouncedValue } from "../../hooks/useDebouncedValue.js";
import { projectService } from "../../services/projectService.js";
import { taskService } from "../../services/taskService.js";
import { apiErrorMessage } from "../../utils/apiErrorMessage.js";
import { filterTasks, sortTasks } from "../../utils/taskFilterSort.js";
import "./TasksPage.css";

function TasksPage() {
  const navigate = useNavigate();
  const [projects, setProjects] = useState([]);

  useEffect(() => {
    let isCurrent = true;
    projectService
      .list()
      .then((data) => {
        if (isCurrent) setProjects(data || []);
      })
      .catch(() => {
        if (isCurrent) setProjects([]);
      });
    return () => {
      isCurrent = false;
    };
  }, []);

  const {
    status,
    priority,
    due,
    project,
    search,
    sortBy,
    order,
    setStatus,
    setPriority,
    setDue,
    setProject,
    setSearch,
    setSort,
    toggleOrder,
    clearFilters,
    hasActiveFilters,
  } = useTaskFilters();

  const debouncedSearch = useDebouncedValue(search, 350);
  const isSearchActive = Boolean(debouncedSearch.trim());
  const hasClientFilters = Boolean(status || priority || due || project);

  const { tasks, isLoading, error, refetch, replaceTask, removeTask } = useTasks(
    null,
    debouncedSearch
  );

  const isSearching = isSearchActive && isLoading;

  const [editingTask, setEditingTask] = useState(null);
  const [deletingTask, setDeletingTask] = useState(null);
  const [isSaving, setIsSaving] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [formError, setFormError] = useState("");
  const [deleteError, setDeleteError] = useState("");
  const [quickUpdateError, setQuickUpdateError] = useState("");

  const visibleTasks = useMemo(() => {
    const filtered = filterTasks(tasks, { status, priority, due, project });
    return sortTasks(filtered, sortBy, order);
  }, [tasks, status, priority, due, project, sortBy, order]);

  const selectedProject = useMemo(() => {
    if (!project) return null;
    return projects.find((p) => String(p.id) === String(project)) || null;
  }, [projects, project]);

  const showNoTasksYet = !isSearchActive && !hasClientFilters && tasks.length === 0;
  const showNoSearchResults = isSearchActive && tasks.length === 0;
  const showNoFilterResults = (tasks.length > 0 || hasClientFilters) && visibleTasks.length === 0;

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
    <PageContainer
      title="Tasks"
      subtitle="All tasks across your projects"
      actions={
        <Button variant="secondary" onClick={() => navigate("/projects")}>
          <FolderKanban size={16} aria-hidden="true" />
          Projects
        </Button>
      }
    >
      {showToolbar && (
        <>
          <div className="tasks-page__toolbar">
            <div style={{ flex: 1, minWidth: 0 }}>
              <TaskFilters
                projects={projects}
                projectId={project}
                onProjectChange={setProject}
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
            <TaskSort
              sortBy={sortBy}
              order={order}
              onSortChange={setSort}
              onToggleOrder={toggleOrder}
            />
          </div>

          <ActiveFilters
            project={project}
            projectName={selectedProject?.name}
            status={status}
            priority={priority}
            due={due}
            search={search}
            onClearProject={() => setProject("")}
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

      {!error && isLoading && <TaskList tasks={[]} isLoading showProject />}

      {!error && !isLoading && showNoTasksYet && (
        <Card className="tasks-page__empty-card">
          <EmptyState
            icon={<CheckSquare size={24} aria-hidden="true" />}
            title="No tasks yet"
            description="Create a task inside one of your projects to get started."
            action={
              <Button variant="primary" onClick={() => navigate("/projects")}>
                <FolderKanban size={16} aria-hidden="true" />
                Go to Projects
              </Button>
            }
          />
        </Card>
      )}

      {!error && !isLoading && showNoSearchResults && (
        <Card className="tasks-page__empty-card">
          <EmptyState
            icon={<SearchX size={24} aria-hidden="true" />}
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
        <Card className="tasks-page__empty-card">
          <EmptyState
            icon={<SearchX size={24} aria-hidden="true" />}
            title="No tasks found"
            description="Try changing your search or filters."
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
          showProject
          onStatusChange={handleStatusChange}
          onPriorityChange={handlePriorityChange}
          onToggleComplete={handleToggleComplete}
          onEdit={setEditingTask}
          onDelete={setDeletingTask}
        />
      )}

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
    </PageContainer>
  );
}

export default TasksPage;
