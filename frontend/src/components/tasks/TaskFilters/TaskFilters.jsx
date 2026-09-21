import { Search, X } from "lucide-react";
import Spinner from "../../Spinner/Spinner.jsx";
import "../TaskFilterBar/TaskFilterBar.css";
import { TASK_STATUS_FILTERS } from "../../../utils/taskStatus.js";
import { TASK_PRIORITIES, TASK_PRIORITY_META } from "../../../utils/taskPriority.js";
import { DUE_FILTERS } from "../../../utils/taskFilterSort.js";

function TaskFilters({
  status,
  onStatusChange,
  priority,
  onPriorityChange,
  due,
  onDueChange,
  search,
  onSearchChange,
  isSearching,
}) {
  return (
    <div className="task-filter-bar">
      <label className="task-filter-bar__search">
        {isSearching ? <Spinner size="sm" label="Searching" /> : <Search size={16} aria-hidden="true" />}
        <input
          type="search"
          placeholder="Search tasks..."
          aria-label="Search tasks"
          value={search}
          onChange={(event) => onSearchChange(event.target.value)}
        />
        {search && (
          <button
            type="button"
            className="task-filter-bar__search-clear"
            aria-label="Clear search"
            onClick={() => onSearchChange("")}
          >
            <X size={14} aria-hidden="true" />
          </button>
        )}
      </label>

      <select
        className="filter-select"
        aria-label="Filter by status"
        data-active={Boolean(status)}
        value={status}
        onChange={(event) => onStatusChange(event.target.value)}
      >
        {TASK_STATUS_FILTERS.map(({ value, label }) => (
          <option key={value || "all"} value={value}>
            {value ? label : "Status: All"}
          </option>
        ))}
      </select>

      <select
        className="filter-select"
        aria-label="Filter by priority"
        data-active={Boolean(priority)}
        value={priority}
        onChange={(event) => onPriorityChange(event.target.value)}
      >
        <option value="">Priority: All</option>
        {TASK_PRIORITIES.map((value) => (
          <option key={value} value={value}>
            {TASK_PRIORITY_META[value].label}
          </option>
        ))}
      </select>

      <select
        className="filter-select"
        aria-label="Filter by due date"
        data-active={Boolean(due)}
        value={due}
        onChange={(event) => onDueChange(event.target.value)}
      >
        {DUE_FILTERS.map(({ value, label }) => (
          <option key={value || "all"} value={value}>
            {value ? label : "Due: All"}
          </option>
        ))}
      </select>
    </div>
  );
}

export default TaskFilters;