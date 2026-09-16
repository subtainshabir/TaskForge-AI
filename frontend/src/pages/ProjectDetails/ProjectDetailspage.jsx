import { useCallback, useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import {
  ArrowLeft,
  LayoutList,
  CheckSquare,
  StickyNote,
  Sparkles,
  Activity,
  Pencil,
  Trash2,
} from "lucide-react";
import PageContainer from "../../components/PageContainer/PageContainer.jsx";
import Card from "../../components/Card/Card.jsx";
import Badge from "../../components/Badge/Badge.jsx";
import Button from "../../components/Button/Button.jsx";
import Modal from "../../components/Modal/Modal.jsx";
import Spinner from "../../components/Spinner/Spinner.jsx";
import { ErrorState } from "../../components/StatePanel/StatePanel.jsx";
import ProjectForm from "../../components/projects/ProjectForm/ProjectForm.jsx";
import DeleteProjectDialog from "../../components/projects/DeleteProjectDialog/DeleteProjectDialog.jsx";
import { projectService } from "../../services/projectService.js";
import { apiErrorMessage } from "../../utils/apiErrorMessage.js";
import { formatAbsoluteDate } from "../../utils/date.js";
import { STATUS_META } from "../../utils/projectStatus.js";
import "./ProjectDetailsPage.css";

const SECTIONS = [
  { id: "overview", label: "Overview", icon: LayoutList, enabled: true },
  { id: "tasks", label: "Tasks", icon: CheckSquare, enabled: false },
  { id: "notes", label: "Notes", icon: StickyNote, enabled: false },
  { id: "ai", label: "AI", icon: Sparkles, enabled: false },
  { id: "activity", label: "Activity", icon: Activity, enabled: false },
];

function ProjectDetailsPage() {
  const { projectId } = useParams();
  const navigate = useNavigate();

  const [project, setProject] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");

  const [isEditOpen, setIsEditOpen] = useState(false);
  const [isDeleteOpen, setIsDeleteOpen] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [formError, setFormError] = useState("");
  const [deleteError, setDeleteError] = useState("");

  const loadProject = useCallback(async () => {
    setIsLoading(true);
    setError("");
    try {
      const data = await projectService.get(projectId);
      setProject(data);
    } catch (err) {
      setError(apiErrorMessage(err, "This project doesn't exist or you don't have access to it."));
    } finally {
      setIsLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    loadProject();
  }, [loadProject]);

  async function handleUpdate(payload) {
    setIsSaving(true);
    setFormError("");
    try {
      const updated = await projectService.update(projectId, payload);
      setProject(updated);
      setIsEditOpen(false);
    } catch (err) {
      setFormError(apiErrorMessage(err, "This project no longer exists."));
    } finally {
      setIsSaving(false);
    }
  }

  async function handleDelete() {
    setIsDeleting(true);
    setDeleteError("");
    try {
      await projectService.remove(projectId);
      navigate("/projects", { replace: true });
    } catch (err) {
      setDeleteError(apiErrorMessage(err, "This project no longer exists."));
    } finally {
      setIsDeleting(false);
    }
  }

  if (isLoading) {
    return (
      <PageContainer>
        <div style={{ display: "flex", justifyContent: "center", padding: "var(--space-16) 0" }}>
          <Spinner size="lg" label="Loading project" />
        </div>
      </PageContainer>
    );
  }

  if (error || !project) {
    return (
      <PageContainer>
        <Card>
          <ErrorState
            title="Project not found"
            description={error || "This project doesn't exist or you don't have access to it."}
            action={
              <Button variant="secondary" onClick={() => navigate("/projects")}>
                Back to Projects
              </Button>
            }
          />
        </Card>
      </PageContainer>
    );
  }

  const { label, icon: StatusIcon, badgeVariant } = STATUS_META[project.status];

  return (
    <PageContainer
      title={project.name}
      subtitle={
        <Badge variant={badgeVariant}>
          <StatusIcon size={12} aria-hidden="true" />
          {label}
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
      <Link to="/projects" className="project-details__back">
        <ArrowLeft size={14} aria-hidden="true" />
        Back to Projects
      </Link>

      <div className="project-details__nav" role="tablist" aria-label="Project sections">
        {SECTIONS.map(({ id, label: sectionLabel, icon: Icon, enabled }) => (
          <button
            key={id}
            type="button"
            role="tab"
            className="project-details__nav-item"
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
        <h2 className="project-details__section-title">Overview</h2>
        <p className="project-details__description">
          {project.description || "No description provided."}
        </p>

        <div className="project-details__meta">
          <div className="project-details__meta-row">
            <span className="project-details__meta-label">Status</span>
            <Badge variant={badgeVariant}>
              <StatusIcon size={12} aria-hidden="true" />
              {label}
            </Badge>
          </div>
          <div className="project-details__meta-row">
            <span className="project-details__meta-label">Created</span>
            <span className="project-details__meta-value">{formatAbsoluteDate(project.created_at)}</span>
          </div>
          <div className="project-details__meta-row">
            <span className="project-details__meta-label">Last updated</span>
            <span className="project-details__meta-value">{formatAbsoluteDate(project.updated_at)}</span>
          </div>
        </div>
      </Card>

      <Modal
        open={isEditOpen}
        onClose={() => {
          setIsEditOpen(false);
          setFormError("");
        }}
        title="Edit project"
      >
        <ProjectForm
          initialValues={project}
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

      <DeleteProjectDialog
        project={project}
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

export default ProjectDetailsPage;