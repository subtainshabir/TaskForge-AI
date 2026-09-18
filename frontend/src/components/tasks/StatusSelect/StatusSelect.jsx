import { ChevronDown } from "lucide-react";
import { TASK_STATUSES, TASK_STATUS_META } from "../../../utils/taskStatus.js";
import "./StatusSelect.css";

function StatusSelect({ value, onChange, disabled, label }) {
  const { badgeVariant } = TASK_STATUS_META[value];

  return (
    <span className={`status-select status-select--${badgeVariant}`}>
      <select
        value={value}
        disabled={disabled}
        aria-label={label || "Task status"}
        onClick={(event) => event.stopPropagation()}
        onChange={(event) => {
          event.stopPropagation();
          onChange(event.target.value);
        }}
      >
        {TASK_STATUSES.map((status) => (
          <option key={status} value={status}>
            {TASK_STATUS_META[status].label}
          </option>
        ))}
      </select>
      <ChevronDown size={12} className="status-select__chevron" aria-hidden="true" />
    </span>
  );
}

export default StatusSelect;