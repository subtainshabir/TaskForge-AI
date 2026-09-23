import { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { ArrowRight, CheckSquare, FolderKanban, Plus } from "lucide-react";
import PageContainer from "../../components/PageContainer/PageContainer.jsx";
import Card from "../../components/Card/Card.jsx";
import Badge from "../../components/Badge/Badge.jsx";
import Button from "../../components/Button/Button.jsx";
import Modal from "../../components/Modal/Modal.jsx";
import Spinner from "../../components/Spinner/Spinner.jsx";
import { EmptyState, ErrorState } from "../../components/StatePanel/StatePanel.jsx";
import ProjectCard from "../../components/projects/ProjectCard/ProjectCard.jsx";
import ProjectForm from "../../components/projects/ProjectForm/ProjectForm.jsx";
import DeleteProjectDialog from "../../components/projects/DeleteProjectDialog/DeleteProjectDialog.jsx";
import TaskList from "../../components/tasks/TaskList/TaskList.jsx";
import TaskForm from "../../components/tasks/TaskForm/TaskForm.jsx";
import DeleteTaskDialog from "../../components/tasks/DeleteTaskDialog/DeleteTaskDialog.jsx";
import { projectService } from "../../services/projectService.js";
import { taskService } from "../../services/taskService.js";
import { apiErrorMessage } from "../../utils/apiErrorMessage.js";
import "./DashBoard.css";

function Dashboard() {
  const navigate = useNavigate();
  const [projects, setProjects] = useState([]);
  const [tasks, setTasks] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");

  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [editingProject, setEditingProject] = useState(null);
  const [deletingProject, setDeletingProject] = useState(null);

  const [editingTask, setEditingTask] = useState(null);
  const [deletingTask, setDeletingTask] = useState(null);

  const [isSaving, setIsSaving] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [formError, setFormError] = useState("");
  const [deleteError, setDeleteError] = useState("");
  const [quickUpdateError, setQuickUpdateError] = useState("");

  const loadData = useCallback(async () => {
    setIsLoading(true);
    setError("");
    try {
      const [projectsData, tasksData] = await Promise.all([
        projectService.list(),
        taskService.listAll(),
      ]);
      setProjects(projectsData || []);
      setTasks(tasksData || []);
    } catch (err) {
      setError(apiErrorMessage(err, "Failed to load dashboard data."));
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
    const handleFocus = () => loadData();
    window.addEventListener("focus", handleFocus);
    return () => window.removeEventListener("focus", handleFocus);
  }, [loadData]);

  const activeProjectsCount = useMemo(
    () => projects.filter((p) => p.status === "active").length,
    [projects]
  );

  const openTasksCount = useMemo(
    () =>
      tasks.filter(
        (t) => t.status === "todo" || t.status === "in_progress" || t.status === "blocked"
      ).length,
    [tasks]
  );

  const completedThisWeekCount = useMemo(() => {
    const weekAgo = new Date(Date.now() - 7 * 24 * 60 * 60 * 1000);
    return tasks.filter(
      (t) => t.status === "completed" && new Date(t.updated_at || t.created_at) >= weekAgo
    ).length;
  }, [tasks]);

  const statusCounts = useMemo(() => {
    let inProgress = 0;
    let todo = 0;
    let blocked = 0;
    let urgent = 0;
    let completed = 0;

    tasks.forEach((t) => {
      if (t.status === "in_progress") inProgress += 1;
      else if (t.status === "todo") todo += 1;
      else if (t.status === "completed") completed += 1;

      if (t.is_blocked || t.status === "blocked") blocked += 1;
      if (t.priority === "urgent" && t.status !== "completed" && t.status !== "cancelled") {
        urgent += 1;
      }
    });

    return { inProgress, todo, blocked, urgent, completed };
  }, [tasks]);

  const recentProjects = useMemo(() => {
    return [...projects]
      .sort((a, b) => new Date(b.updated_at) - new Date(a.updated_at))
      .slice(0, 3);
  }, [projects]);

  const recentTasks = useMemo(() => {
    return [...tasks]
      .sort((a, b) => new Date(b.updated_at || b.created_at) - new Date(a.updated_at || a.created_at))
      .slice(0, 5);
  }, [tasks]);

  async function handleProjectCreate(payload) {
    setIsSaving(true);
    setFormError("");
    try {
      const created = await projectService.create(payload);
      setProjects((prev) => [created, ...prev]);
      setIsCreateOpen(false);
    } catch (err) {
      setFormError(apiErrorMessage(err));
    } finally {
      setIsSaving(false);
    }
  }

  async function handleProjectUpdate(payload) {
    if (!editingProject) return;
    setIsSaving(true);
    setFormError("");
    try {
      const updated = await projectService.update(editingProject.id, payload);
      setProjects((prev) => prev.map((p) => (p.id === updated.id ? updated : p)));
      setEditingProject(null);
    } catch (err) {
      setFormError(apiErrorMessage(err, "This project no longer exists."));
    } finally {
      setIsSaving(false);
    }
  }

  async function handleProjectDelete() {
    if (!deletingProject) return;
    setIsDeleting(true);
    setDeleteError("");
    try {
      await projectService.remove(deletingProject.id);
      setProjects((prev) => prev.filter((p) => p.id !== deletingProject.id));
      setTasks((prev) => prev.filter((t) => t.project_id !== deletingProject.id));
      setDeletingProject(null);
    } catch (err) {
      setDeleteError(apiErrorMessage(err, "This project no longer exists."));
    } finally {
      setIsDeleting(false);
    }
  }

  async function handleTaskUpdate(payload) {
    if (!editingTask) return;
    setIsSaving(true);
    setFormError("");
    try {
      const updated = await taskService.update(editingTask.id, payload);
      setTasks((prev) => prev.map((t) => (t.id === updated.id ? updated : t)));
      setEditingTask(null);
    } catch (err) {
      setFormError(apiErrorMessage(err, "This task no longer exists."));
    } finally {
      setIsSaving(false);
    }
  }

  async function handleTaskDelete() {
    if (!deletingTask) return;
    setIsDeleting(true);
    setDeleteError("");
    try {
      await taskService.remove(deletingTask.id);
      setTasks((prev) => prev.filter((t) => t.id !== deletingTask.id));
      setDeletingTask(null);
    } catch (err) {
      setDeleteError(apiErrorMessage(err, "This task no longer exists."));
    } finally {
      setIsDeleting(false);
    }
  }

  async function handleStatusChange(task, nextStatus) {
    const previous = task.status;
    setTasks((prev) =>
      prev.map((t) => (t.id === task.id ? { ...t, status: nextStatus, updated_at: new Date().toISOString() } : t))
    );
    setQuickUpdateError("");
    try {
      const updated = await taskService.update(task.id, { status: nextStatus });
      setTasks((prev) => prev.map((t) => (t.id === updated.id ? updated : t)));
    } catch (err) {
      setTasks((prev) => prev.map((t) => (t.id === task.id ? { ...t, status: previous } : t)));
      setQuickUpdateError(apiErrorMessage(err, "Unable to update task status. Please try again."));
    }
  }

  async function handlePriorityChange(task, nextPriority) {
    const previous = task.priority;
    setTasks((prev) =>
      prev.map((t) => (t.id === task.id ? { ...t, priority: nextPriority, updated_at: new Date().toISOString() } : t))
    );
    setQuickUpdateError("");
    try {
      const updated = await taskService.update(task.id, { priority: nextPriority });
      setTasks((prev) => prev.map((t) => (t.id === updated.id ? updated : t)));
    } catch (err) {
      setTasks((prev) => prev.map((t) => (t.id === task.id ? { ...t, priority: previous } : t)));
      setQuickUpdateError(apiErrorMessage(err, "Unable to update task priority. Please try again."));
    }
  }

  async function handleToggleComplete(task) {
    const nextStatus = task.status === "completed" ? "todo" : "completed";
    await handleStatusChange(task, nextStatus);
  }

  return (
    <PageContainer
      title="Dashboard"
      subtitle="An overview of your workspace"
      actions={
        <Button variant="primary" onClick={() => setIsCreateOpen(true)}>
          <Plus size={16} aria-hidden="true" />
          New project
        </Button>
      }
    >
      {error && !isLoading && (
        <Card style={{ marginBottom: "var(--space-6)" }}>
          <ErrorState
            title="Couldn't load dashboard"
            description={error}
            action={
              <Button variant="secondary" onClick={loadData}>
                Try again
              </Button>
            }
          />
        </Card>
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

      <div className="dashboard__summary">
        <Card>
          <p className="dashboard__summary-label">Active projects</p>
          <p className="dashboard__summary-value">
            {isLoading ? "—" : activeProjectsCount}
          </p>
        </Card>
        <Card>
          <p className="dashboard__summary-label">Open tasks</p>
          <p className="dashboard__summary-value">
            {isLoading ? "—" : openTasksCount}
          </p>
        </Card>
        <Card>
          <p className="dashboard__summary-label">Completed this week</p>
          <p className="dashboard__summary-value">
            {isLoading ? "—" : completedThisWeekCount}
          </p>
        </Card>
      </div>

      <div className="dashboard__badges">
        <Badge variant="ai">In Progress: {statusCounts.inProgress}</Badge>
        <Badge variant="neutral">Todo: {statusCounts.todo}</Badge>
        {statusCounts.blocked > 0 && (
          <Badge variant="danger">Blocked: {statusCounts.blocked}</Badge>
        )}
        {statusCounts.urgent > 0 && (
          <Badge variant="danger">Urgent: {statusCounts.urgent}</Badge>
        )}
        <Badge variant="success">Completed: {statusCounts.completed}</Badge>
      </div>

      {isLoading && (
        <div style={{ display: "flex", justifyContent: "center", padding: "var(--space-8) 0" }}>
          <Spinner size="lg" label="Loading dashboard" />
        </div>
      )}

      {!isLoading && !error && projects.length === 0 && (
        <Card className="dashboard__empty-card">
          <EmptyState
            icon={<FolderKanban size={22} aria-hidden="true" />}
            title="No projects yet"
            description="Create your first project to start breaking work into tasks with TaskForge AI."
            action={
              <Button variant="primary" onClick={() => setIsCreateOpen(true)}>
                <Plus size={16} aria-hidden="true" />
                New project
              </Button>
            }
          />
        </Card>
      )}

      {!isLoading && !error && projects.length > 0 && (
        <>
          <section className="dashboard__section" aria-labelledby="recent-projects-heading">
            <div className="dashboard__section-header">
              <h2 id="recent-projects-heading" className="dashboard__section-title">
                Recent Projects
              </h2>
              <Link to="/projects" className="dashboard__section-link">
                View all
                <ArrowRight size={14} aria-hidden="true" />
              </Link>
            </div>
            <div className="dashboard__projects-grid">
              {recentProjects.map((project) => (
                <ProjectCard
                  key={project.id}
                  project={project}
                  onEdit={setEditingProject}
                  onDelete={setDeletingProject}
                />
              ))}
            </div>
          </section>

          <section className="dashboard__section" aria-labelledby="recent-tasks-heading">
            <div className="dashboard__section-header">
              <h2 id="recent-tasks-heading" className="dashboard__section-title">
                Recent Tasks
              </h2>
              <Link to="/tasks" className="dashboard__section-link">
                View all
                <ArrowRight size={14} aria-hidden="true" />
              </Link>
            </div>
            {recentTasks.length === 0 ? (
              <Card>
                <EmptyState
                  icon={<CheckSquare size={20} aria-hidden="true" />}
                  title="No tasks yet"
                  description="Add tasks to your projects to start tracking progress."
                  action={
                    <Button variant="secondary" onClick={() => navigate(`/projects/${projects[0].id}`)}>
                      Go to {projects[0].name}
                    </Button>
                  }
                />
              </Card>
            ) : (
              <TaskList
                tasks={recentTasks}
                isLoading={false}
                showProject
                onStatusChange={handleStatusChange}
                onPriorityChange={handlePriorityChange}
                onToggleComplete={handleToggleComplete}
                onEdit={setEditingTask}
                onDelete={setDeletingTask}
              />
            )}
          </section>
        </>
      )}

      <Modal
        open={isCreateOpen}
        onClose={() => {
          setIsCreateOpen(false);
          setFormError("");
        }}
        title="Create project"
      >
        <ProjectForm
          submitLabel="Create project"
          isSubmitting={isSaving}
          apiError={formError}
          onSubmit={handleProjectCreate}
          onCancel={() => {
            setIsCreateOpen(false);
            setFormError("");
          }}
        />
      </Modal>

      <Modal
        open={Boolean(editingProject)}
        onClose={() => {
          setEditingProject(null);
          setFormError("");
        }}
        title="Edit project"
      >
        {editingProject && (
          <ProjectForm
            initialValues={editingProject}
            submitLabel="Save changes"
            isSubmitting={isSaving}
            apiError={formError}
            onSubmit={handleProjectUpdate}
            onCancel={() => {
              setEditingProject(null);
              setFormError("");
            }}
          />
        )}
      </Modal>

      <DeleteProjectDialog
        project={deletingProject}
        open={Boolean(deletingProject)}
        isDeleting={isDeleting}
        apiError={deleteError}
        onConfirm={handleProjectDelete}
        onCancel={() => {
          setDeletingProject(null);
          setDeleteError("");
        }}
      />

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
            onSubmit={handleTaskUpdate}
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
        onConfirm={handleTaskDelete}
        onCancel={() => {
          setDeletingTask(null);
          setDeleteError("");
        }}
      />
    </PageContainer>
  );
}

export default Dashboard;