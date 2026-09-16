import ProjectCard from "../ProjectCard/ProjectCard.jsx";
import "./ProjectGrid.css";

function ProjectGrid({ projects, isLoading, onEdit, onDelete }) {
  if (isLoading) {
    return (
      <div className="project-grid" aria-hidden="true">
        {Array.from({ length: 6 }).map((_, index) => (
          <div key={index} className="project-card-skeleton" />
        ))}
      </div>
    );
  }

  return (
    <div className="project-grid">
      {projects.map((project) => (
        <ProjectCard key={project.id} project={project} onEdit={onEdit} onDelete={onDelete} />
      ))}
    </div>
  );
}

export default ProjectGrid;