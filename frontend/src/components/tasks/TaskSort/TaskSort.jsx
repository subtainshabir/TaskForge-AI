import { ArrowUp, ArrowDown } from "lucide-react";
import "../TaskFilterBar/TaskFilterBar.css";
import { SORT_OPTIONS, SORT_TOGGLEABLE } from "../../../utils/taskFilterSort.js";

function TaskSort({ sortBy, order, onSortChange, onToggleOrder }) {
  const canToggle = SORT_TOGGLEABLE.has(sortBy);

  return (
    <div className="task-sort">
      <select
        className="filter-select"
        aria-label="Sort tasks"
        value={sortBy}
        onChange={(event) => onSortChange(event.target.value)}
      >
        {SORT_OPTIONS.map(({ value, label }) => (
          <option key={value} value={value}>
            Sort: {label}
          </option>
        ))}
      </select>

      <button
        type="button"
        className="task-sort__toggle"
        onClick={onToggleOrder}
        disabled={!canToggle}
        aria-label={order === "asc" ? "Sort ascending, switch to descending" : "Sort descending, switch to ascending"}
        title={canToggle ? "Toggle sort direction" : undefined}
      >
        {order === "asc" ? <ArrowUp size={15} aria-hidden="true" /> : <ArrowDown size={15} aria-hidden="true" />}
      </button>
    </div>
  );
}

export default TaskSort;