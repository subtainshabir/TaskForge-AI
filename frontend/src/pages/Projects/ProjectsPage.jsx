import { useMemo, useState } from "react";
import { FolderKanban, Plus, SearchX } from "lucide-react";
import PageContainer from "../../components/PageContainer/PageContainer.jsx";
import Card from "../../components/Card/Card.jsx";
import Button from "../../components/Button/Button.jsx";
import Modal from "../../components/Modal/Modal.jsx";
import { EmptyState, ErrorState } from "../../components/StatePanel/StatePanel.jsx";
import ProjectFilters from "../../components/projects/ProjectFilters/ProjectFilters.jsx";
import ProjectGrid from "../../components/projects/ProjectGrid/ProjectGrid.jsx";
import ProjectForm from "../../components/projects/ProjectForm/ProjectForm.jsx";
import DeleteProjectDialog from "../../components/projects/DeleteProjectDialog/DeleteProjectDialog.jsx";
import { useProjects } from "../../hooks/useProjects.js";
import { projectService } from "../../services/projectService.js";
import { apiErrorMessage } from "../../utils/apiErrorMessage.js";
import "./ProjectsPage.css";

function ProjectsPage() {
  const { projects, isLoading, error, refetch, addProject, replaceProject, removeProject } =
    useProjects();

  const [statusFilter, setStatusFilter] = useState("");
  const [search, setSearch] = useState("");

  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [editingProject, setEditingProject] = useState(null);
  const [deletingProject, setDeletingProject] = useState(null);

  const [isSaving, setIsSaving] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [formError, setFormError] = useState("");
  const [deleteError, setDeleteError] = useState("");

  const filteredProjects = useMemo(() => {
    const query = search.trim().toLowerCase();
    return projects.filter((project) => {
      const matchesStatus = !statusFilter || project.status === statusFilter;
      const matchesSearch =
        !query ||
        project.name.toLowerCase().includes(query) ||
        (project.description || "").toLowerCase().includes(query);
      return matchesStatus && matchesSearch;
    });
  }, [projects, statusFilter, search]);

  const hasAnyProjects = projects.length > 0;
  const hasActiveFilters = Boolean(statusFilter || search.trim());

  async function handleCreate(payload) {
    setIsSaving(true);
    setFormError("");
    try {
      const created = await projectService.create(payload);
      addProject(created);
      setIsCreateOpen(false);
    } catch (err) {
      setFormError(apiErrorMessage(err));
    } finally {
      setIsSaving(false);
    }
  }

  async function handleUpdate(payload) {
    if (!editingProject) return;
    setIsSaving(true);
    setFormError("");
    try {
      const updated = await projectService.update(editingProject.id, payload);
      replaceProject(updated);
      setEditingProject(null);
    } catch (err) {
      setFormError(apiErrorMessage(err, "This project no longer exists."));
    } finally {
      setIsSaving(false);
    }
  }

  async function handleDelete() {
    if (!deletingProject) return;
    setIsDeleting(true);
    setDeleteError("");
    try {
      await projectService.remove(deletingProject.id);
      removeProject(deletingProject.id);
      setDeletingProject(null);
    } catch (err) {
      setDeleteError(apiErrorMessage(err, "This project no longer exists."));
    } finally {
      setIsDeleting(false);
    }
  }

  return (
    <PageContainer
      title="Projects"
      subtitle="Manage your workspaces and projects"
      actions={
        <Button variant="primary" onClick={() => setIsCreateOpen(true)}>
          <Plus size={16} aria-hidden="true" />
          New Project
        </Button>
      }
    >
      {hasAnyProjects && (
        <ProjectFilters
          status={statusFilter}
          onStatusChange={setStatusFilter}
          search={search}
          onSearchChange={setSearch}
        />
      )}

      {error && !isLoading && (
        <Card>
          <ErrorState
            title="Couldn't load your projects"
            description={error}
            action={
              <Button variant="secondary" onClick={refetch}>
                Try again
              </Button>
            }
          />
        </Card>
      )}

      {!error && isLoading && <ProjectGrid projects={[]} isLoading />}

      {!error && !isLoading && !hasAnyProjects && (
        <Card className="projects-page__empty-card">
          <EmptyState
            icon={<FolderKanban size={22} aria-hidden="true" />}
            title="No projects yet"
            description="Create your first project and start turning your ideas into structured work."
            action={
              <Button variant="primary" onClick={() => setIsCreateOpen(true)}>
                <Plus size={16} aria-hidden="true" />
                Create Project
              </Button>
            }
          />
        </Card>
      )}

      {!error && !isLoading && hasAnyProjects && filteredProjects.length === 0 && (
        <Card className="projects-page__empty-card">
          <EmptyState
            icon={<SearchX size={22} aria-hidden="true" />}
            title="No projects match your filters"
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

      {!error && !isLoading && filteredProjects.length > 0 && (
        <ProjectGrid
          projects={filteredProjects}
          isLoading={false}
          onEdit={setEditingProject}
          onDelete={setDeletingProject}
        />
      )}

      <Modal
        open={isCreateOpen}
        onClose={() => {
          setIsCreateOpen(false);
          setFormError("");
        }}
        title="New project"
      >
        <ProjectForm
          submitLabel="Create project"
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
            onSubmit={handleUpdate}
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
        onConfirm={handleDelete}
        onCancel={() => {
          setDeletingProject(null);
          setDeleteError("");
        }}
      />
    </PageContainer>
  );
}

export default ProjectsPage;