import { useCallback, useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import PageContainer from "../../components/PageContainer/PageContainer.jsx";
import Card from "../../components/Card/Card.jsx";
import Button from "../../components/Button/Button.jsx";
import Modal from "../../components/Modal/Modal.jsx";
import { ErrorState } from "../../components/StatePanel/StatePanel.jsx";
import TaskHeader from "../../components/tasks/TaskHeader/TaskHeader.jsx";
import TaskStatusControl from "../../components/tasks/TaskStatusControl/TaskStatusControl.jsx";
import TaskPriorityControl from "../../components/tasks/TaskPriorityControl/TaskPriorityControl.jsx";
import TaskDueDateControl from "../../components/tasks/TaskDueDateControl/TaskDueDateControl.jsx";
import TaskDescription from "../../components/tasks/TaskDescription/TaskDescription.jsx";
import TaskMetadata from "../../components/tasks/TaskMetadata/TaskMetadata.jsx";
import TaskForm from "../../components/tasks/TaskForm/TaskForm.jsx";
import DeleteTaskDialog from "../../components/tasks/DeleteTaskDialog/DeleteTaskDialog.jsx";
import TaskDependencies from "../../components/tasks/TaskDependencies/TaskDependencies.jsx";
import TaskPhases from "../../components/tasks/TaskPhases/TaskPhases.jsx";
import TaskAIAnalysis from "../../components/tasks/TaskAIAnalysis/TaskAIAnalysis.jsx";
import TaskActivity from "../../components/tasks/TaskActivity/TaskActivity.jsx";
import { taskService } from "../../services/taskService.js";
import { projectService } from "../../services/projectService.js";
import { apiErrorMessage } from "../../utils/apiErrorMessage.js";
import "./TaskDetailsPage.css";

function TaskDetailsSkeleton() {
  return (
    <PageContainer>
      <div className="task-details__skeleton-line" style={{ width: 220, height: 16, marginBottom: 16 }} />
      <div className="task-details__skeleton-line" style={{ width: 320, height: 32, marginBottom: 24 }} />
      <div style={{ display: "flex", gap: 12, marginBottom: 24 }}>
        <div className="task-details__skeleton-line" style={{ width: 90, height: 28 }} />
        <div className="task-details__skeleton-line" style={{ width: 90, height: 28 }} />
        <div className="task-details__skeleton-line" style={{ width: 120, height: 28 }} />
      </div>
      <div className="task-details__skeleton-line" style={{ width: "100%", height: 160 }} />
    </PageContainer>
  );
}

function TaskDetailsPage() {
  const { projectId, taskId } = useParams();
  const navigate = useNavigate();

  const [task, setTask] = useState(null);
  const [project, setProject] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");

  const [isEditOpen, setIsEditOpen] = useState(false);
  const [isDeleteOpen, setIsDeleteOpen] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [formError, setFormError] = useState("");
  const [deleteError, setDeleteError] = useState("");
  const [activityRefreshKey, setActivityRefreshKey] = useState(0);

  const triggerActivityRefresh = () => setActivityRefreshKey((k) => k + 1);

  const handlePhaseChange = useCallback(async () => {
    triggerActivityRefresh();
    try {
      const updated = await taskService.get(taskId);
      setTask(updated);
    } catch {
      // ignore
    }
  }, [taskId]);

  const handleBlockedChange = useCallback((isBlocked) => {
    setTask((prev) => {
      if (!prev || prev.is_blocked === isBlocked) return prev;
      return { ...prev, is_blocked: isBlocked };
    });
  }, []);

  const loadData = useCallback(async () => {
    setIsLoading(true);
    setError("");
    try {
      const [taskData, projectData] = await Promise.all([
        taskService.get(taskId),
        projectService.get(projectId),
      ]);
      setTask(taskData);
      setProject(projectData);
    } catch (err) {
      setError(apiErrorMessage(err, "This task doesn't exist or you don't have access to it."));
    } finally {
      setIsLoading(false);
    }
  }, [taskId, projectId]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  async function handleUpdate(payload) {
    setIsSaving(true);
    setFormError("");
    try {
      const updated = await taskService.update(taskId, payload);
      setTask(updated);
      setIsEditOpen(false);
      triggerActivityRefresh();
    } catch (err) {
      setFormError(apiErrorMessage(err, "This task no longer exists."));
    } finally {
      setIsSaving(false);
    }
  }

  async function handleDelete() {
    setIsDeleting(true);
    setDeleteError("");
    try {
      await taskService.remove(taskId);
      navigate(`/projects/${projectId}`, { replace: true });
    } catch (err) {
      setDeleteError(apiErrorMessage(err, "This task no longer exists."));
    } finally {
      setIsDeleting(false);
    }
  }

  if (isLoading) {
    return <TaskDetailsSkeleton />;
  }

  if (error || !task) {
    return (
      <PageContainer>
        <Card>
          <ErrorState
            title="Task not found"
            description={error || "This task doesn't exist or you don't have access to it."}
            action={
              <Button variant="secondary" onClick={() => navigate(`/projects/${projectId}`)}>
                Back to Project
              </Button>
            }
          />
        </Card>
      </PageContainer>
    );
  }

  return (
    <PageContainer>
      <TaskHeader
        projectId={projectId}
        projectName={project?.name}
        taskTitle={task.title}
        isCompleted={task.status === "completed"}
        isBlocked={task.is_blocked}
        onEdit={() => setIsEditOpen(true)}
        onDelete={() => setIsDeleteOpen(true)}
      />

      <div className="task-controls">
        <TaskStatusControl
          task={task}
          onUpdated={(updated) => {
            setTask(updated);
            triggerActivityRefresh();
          }}
        />
        <TaskPriorityControl
          task={task}
          onUpdated={(updated) => {
            setTask(updated);
            triggerActivityRefresh();
          }}
        />
        <TaskDueDateControl
          task={task}
          onUpdated={(updated) => {
            setTask(updated);
            triggerActivityRefresh();
          }}
        />
      </div>

      <Card>
        <h2 className="task-details__section-title">Overview</h2>
        <TaskDescription description={task.description} />
        <TaskMetadata task={task} />
      </Card>

      <TaskDependencies
        taskId={taskId}
        projectId={projectId}
        onBlockedChange={handleBlockedChange}
        onDependencyChange={triggerActivityRefresh}
      />

      <TaskPhases taskId={taskId} onPhaseChange={handlePhaseChange} />

      <TaskAIAnalysis taskId={taskId} />

      <TaskActivity taskId={taskId} refreshKey={activityRefreshKey} />

      <Modal
        open={isEditOpen}
        onClose={() => {
          setIsEditOpen(false);
          setFormError("");
        }}
        title="Edit task"
      >
        <TaskForm
          initialValues={task}
          submitLabel="Save changes"
          isSubmitting={isSaving}
          apiError={formError}
          onSubmit={handleUpdate}
          onCancel={() => {
            setIsEditOpen(false);
            setFormError("");
          }}
        />
      </Modal>

      <DeleteTaskDialog
        task={task}
        open={isDeleteOpen}
        isDeleting={isDeleting}
        apiError={deleteError}
        onConfirm={handleDelete}
        onCancel={() => {
          setIsDeleteOpen(false);
          setDeleteError("");
        }}
      />
    </PageContainer>
  );
}

export default TaskDetailsPage;