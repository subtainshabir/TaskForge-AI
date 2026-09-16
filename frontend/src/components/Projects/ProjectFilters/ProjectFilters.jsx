import { Search } from "lucide-react";
import { STATUS_FILTERS } from "../../../utils/projectStatus.js";
import "./ProjectFilters.css";

function ProjectFilters({ status, onStatusChange, search, onSearchChange }) {
  return (
    <div className="project-filters">
      <div className="project-filters__status" role="group" aria-label="Filter by status">
        {STATUS_FILTERS.map(({ value, label }) => (
          <button
            key={value || "all"}
            type="button"
            className="project-filters__pill"
            aria-pressed={status === value}
            onClick={() => onStatusChange(value)}
          >
            {label}
          </button>
        ))}
      </div>

      <label className="project-filters__search">
        <Search size={16} aria-hidden="true" />
        <input
          type="search"
          placeholder="Search projects"
          aria-label="Search projects"
          value={search}
          onChange={(event) => onSearchChange(event.target.value)}
        />
      </label>
    </div>
  );
}

export default ProjectFilters;