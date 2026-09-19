import { CalendarClock } from "lucide-react";
import Badge from "../../Badge/Badge.jsx";
import { TASK_STATUS_META } from "../../../utils/taskStatus.js";
import { TASK_PRIORITY_META } from "../../../utils/taskPriority.js";
import { formatAbsoluteDate, getDueDateInfo } from "../../../utils/date.js";
import "./TaskMetadata.css";

function TaskMetadata({ task }) {
  const { label: statusLabel, icon: StatusIcon, badgeVariant: statusVariant } = TASK_STATUS_META[task.status];
  const { label: priorityLabel, icon: PriorityIcon, badgeVariant: priorityVariant } = TASK_PRIORITY_META[task.priority];
  const dueInfo = getDueDateInfo(task.deadline, task.status);

  return (
    <div className="task-metadata">
      <div className="task-metadata__row">
        <span className="task-metadata__label">Status</span>
        <Badge variant={statusVariant}>
          <StatusIcon size={12} aria-hidden="true" />
          {statusLabel}
        </Badge>
      </div>
      <div className="task-metadata__row">
        <span className="task-metadata__label">Priority</span>
        <Badge variant={priorityVariant}>
          <PriorityIcon size={12} aria-hidden="true" />
          {priorityLabel}
        </Badge>
      </div>
      <div className="task-metadata__row">
        <span className="task-metadata__label">Due date</span>
        <span className={`task-metadata__value ${dueInfo.urgency === "overdue" ? "task-metadata__value--overdue" : ""}`}>
          {dueInfo.urgency !== "none" && <CalendarClock size={13} aria-hidden="true" />}
          {dueInfo.label}
        </span>
      </div>
      <div className="task-metadata__row">
        <span className="task-metadata__label">Created</span>
        <span className="task-metadata__value">{formatAbsoluteDate(task.created_at)}</span>
      </div>
      <div className="task-metadata__row">
        <span className="task-metadata__label">Last updated</span>
        <span className="task-metadata__value">{formatAbsoluteDate(task.updated_at)}</span>
      </div>
    </div>
  );
}

export default TaskMetadata;