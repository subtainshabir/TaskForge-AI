import { useCallback, useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import {
  ArrowLeft,
  LayoutList,
  GitBranch,
  TrendingUp,
  StickyNote,
  Sparkles,
  Pencil,
  Trash2,
  CalendarClock,
} from "lucide-react";
import PageContainer from "../../components/PageContainer/PageContainer.jsx";
import Card from "../../components/Card/Card.jsx";
import Badge from "../../components/Badge/Badge.jsx";
import Button from "../../components/Button/Button.jsx";
import Modal from "../../components/Modal/Modal.jsx";
import Spinner from "../../components/Spinner/Spinner.jsx";
import { ErrorState } from "../../components/StatePanel/StatePanel.jsx";
import TaskForm from "../../components/tasks/TaskForm/TaskForm.jsx";
import DeleteTaskDialog from "../../components/tasks/DeleteTaskDialog/DeleteTaskDialog.jsx";
import { taskService } from "../../services/taskService.js";
import { apiErrorMessage } from "../../utils/apiErrorMessage.js";
import { formatAbsoluteDate, formatDueDate, isOverdue } from "../../utils/date.js";
import { TASK_STATUS_META } from "../../utils/taskStatus.js";
import { TASK_PRIORITY_META } from "../../utils/taskPriority.js";
import "./TaskDetailsPage.css";

const SECTIONS = [
  { id: "overview", label: "Overview", icon: LayoutList, enabled: true },
  { id: "phases", label: "AI Phases", icon: GitBranch, enabled: false },
  { id: "progress", label: "Progress", icon: TrendingUp, enabled: false },
  { id: "notes", label: "Notes", icon: StickyNote, enabled: false },
  { id: "chat", label: "AI Chat", icon: Sparkles, enabled: false },
];

function TaskDetailsPage() {
  const { projectId, taskId } = useParams();
  const navigate = useNavigate();

  const [task, setTask] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");

  const [isEditOpen, setIsEditOpen] = useState(false);
  const [isDeleteOpen, setIsDeleteOpen] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [formError, setFormError] = useState("");
  const [deleteError, setDeleteError] = useState("");

  const loadTask = useCallback(async () => {
    setIsLoading(true);
    setError("");
    try {
      const data = await taskService.get(taskId);
      setTask(data);
    } catch (err) {
      setError(apiErrorMessage(err, "This task doesn't exist or you don't have access to it."));
    } finally {
      setIsLoading(false);
    }
  }, [taskId]);

  useEffect(() => {
    loadTask();
  }, [loadTask]);

  async function handleUpdate(payload) {
    setIsSaving(true);
    setFormError("");
    try {
      const updated = await taskService.update(taskId, payload);
      setTask(updated);
      setIsEditOpen(false);
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
    return (
      <PageContainer>
        <div style={{ display: "flex", justifyContent: "center", padding: "var(--space-16) 0" }}>
          <Spinner size="lg" label="Loading task" />
        </div>
      </PageContainer>
    );
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

  const { label: statusLabel, icon: StatusIcon, badgeVariant: statusVariant } = TASK_STATUS_META[task.status];
  const { label: priorityLabel, icon: PriorityIcon, badgeVariant: priorityVariant } = TASK_PRIORITY_META[task.priority];
  const dueLabel = formatDueDate(task.deadline);
  const overdue = isOverdue(task.deadline, task.status);

  return (
    <PageContainer
      title={task.title}
      subtitle={
        <Badge variant={statusVariant}>
          <StatusIcon size={12} aria-hidden="true" />
          {statusLabel}
        </Badge>
      }
      actions={
        <>
          <Button variant="secondary" onClick={() => setIsEditOpen(true)}>
            <Pencil size={16} aria-hidden="true" />
            Edit
          </Button>
          <Button variant="danger" onClick={() => setIsDeleteOpen(true)}>
            <Trash2 size={16} aria-hidden="true" />
            Delete
          </Button>
        </>
      }
    >
      <Link to={`/projects/${projectId}`} className="task-details__back">
        <ArrowLeft size={14} aria-hidden="true" />
        Back to Project
      </Link>

      <div className="task-details__nav" role="tablist" aria-label="Task sections">
        {SECTIONS.map(({ id, label: sectionLabel, icon: Icon, enabled }) => (
          <button
            key={id}
            type="button"
            role="tab"
            className="task-details__nav-item"
            aria-selected={id === "overview"}
            disabled={!enabled}
            title={enabled ? undefined : "Coming soon"}
          >
            <Icon size={16} aria-hidden="true" />
            {sectionLabel}
          </button>
        ))}
      </div>

      <Card>
        <h2 className="task-details__section-title">Overview</h2>
        <p className="task-details__description">{task.description || "No description provided."}</p>

        <div className="task-details__meta">
          <div className="task-details__meta-row">
            <span className="task-details__meta-label">Status</span>
            <Badge variant={statusVariant}>
              <StatusIcon size={12} aria-hidden="true" />
              {statusLabel}
            </Badge>
          </div>
          <div className="task-details__meta-row">
            <span className="task-details__meta-label">Priority</span>
            <Badge variant={priorityVariant}>
              <PriorityIcon size={12} aria-hidden="true" />
              {priorityLabel}
            </Badge>
          </div>
          <div className="task-details__meta-row">
            <span className="task-details__meta-label">Due date</span>
            <span
              className={`task-details__meta-value ${overdue ? "task-details__meta-value--overdue" : ""}`}
            >
              {dueLabel ? (
                <>
                  <CalendarClock size={13} aria-hidden="true" style={{ marginRight: 4, verticalAlign: "-2px" }} />
                  {overdue ? `Overdue · ${dueLabel}` : dueLabel}
                </>
              ) : (
                "No due date"
              )}
            </span>
          </div>
          <div className="task-details__meta-row">
            <span className="task-details__meta-label">Created</span>
            <span className="task-details__meta-value">{formatAbsoluteDate(task.created_at)}</span>
          </div>
          <div className="task-details__meta-row">
            <span className="task-details__meta-label">Last updated</span>
            <span className="task-details__meta-value">{formatAbsoluteDate(task.updated_at)}</span>
          </div>
        </div>
      </Card>

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