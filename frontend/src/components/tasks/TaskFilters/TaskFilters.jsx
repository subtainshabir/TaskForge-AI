import { Search } from "lucide-react";
import "../../projects/ProjectFilters/ProjectFilters.css";
import { TASK_STATUS_FILTERS } from "../../../utils/taskStatus.js";

function TaskFilters({ status, onStatusChange, search, onSearchChange }) {
  return (
    <div className="project-filters">
      <div className="project-filters__status" role="group" aria-label="Filter by status">
        {TASK_STATUS_FILTERS.map(({ value, label }) => (
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
          placeholder="Search tasks"
          aria-label="Search tasks"
          value={search}
          onChange={(event) => onSearchChange(event.target.value)}
        />
      </label>
    </div>
  );
}

export default TaskFilters;