import { X } from "lucide-react";
import "../TaskFilterBar/TaskFilterBar.css";
import { TASK_STATUS_META } from "../../../utils/taskStatus.js";
import { TASK_PRIORITY_META } from "../../../utils/taskPriority.js";
import { DUE_FILTERS } from "../../../utils/taskFilterSort.js";

function ActiveFilters({
  status,
  priority,
  due,
  search,
  project,
  projectName,
  onClearStatus,
  onClearPriority,
  onClearDue,
  onClearSearch,
  onClearProject,
  onClearAll,
}) {
  const chips = [];

  if (project) {
    chips.push({
      key: "project",
      label: `Project: ${projectName || project}`,
      onRemove: onClearProject,
    });
  }
  if (status) {
    chips.push({ key: "status", label: `Status: ${TASK_STATUS_META[status].label}`, onRemove: onClearStatus });
  }
  if (priority) {
    chips.push({ key: "priority", label: `Priority: ${TASK_PRIORITY_META[priority].label}`, onRemove: onClearPriority });
  }
  if (due) {
    const dueLabel = DUE_FILTERS.find((option) => option.value === due)?.label || due;
    chips.push({ key: "due", label: `Due: ${dueLabel}`, onRemove: onClearDue });
  }
  if (search && search.trim()) {
    chips.push({ key: "search", label: `Search: "${search.trim()}"`, onRemove: onClearSearch });
  }

  if (chips.length === 0) return null;

  return (
    <div className="active-filters" aria-label="Active filters">
      <span className="active-filters__label">Filters</span>
      {chips.map((chip) => (
        <span key={chip.key} className="active-filters__chip">
          {chip.label}
          <button
            type="button"
            className="active-filters__chip-remove"
            aria-label={`Remove filter: ${chip.label}`}
            onClick={chip.onRemove}
          >
            <X size={12} aria-hidden="true" />
          </button>
        </span>
      ))}
      <button type="button" className="active-filters__clear" onClick={onClearAll}>
        Clear all
      </button>
    </div>
  );
}

export default ActiveFilters;