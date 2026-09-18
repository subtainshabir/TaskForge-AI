import { ChevronDown } from "lucide-react";
import { TASK_PRIORITIES, TASK_PRIORITY_META } from "../../../utils/taskPriority.js";
import "./PrioritySelect.css";

function PrioritySelect({ value, onChange, disabled, label }) {
  const { badgeVariant } = TASK_PRIORITY_META[value];

  return (
    <span className={`priority-select priority-select--${badgeVariant}`}>
      <select
        value={value}
        disabled={disabled}
        aria-label={label || "Task priority"}
        onChange={(event) => onChange(event.target.value)}
      >
        {TASK_PRIORITIES.map((priority) => (
          <option key={priority} value={priority}>
            {TASK_PRIORITY_META[priority].label}
          </option>
        ))}
      </select>
      <ChevronDown size={12} className="priority-select__chevron" aria-hidden="true" />
    </span>
  );
}

export default PrioritySelect;