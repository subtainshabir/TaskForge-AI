import { useCallback, useEffect, useState } from "react";
import {
  Activity,
  AlertCircle,
  CalendarClock,
  CheckCircle2,
  GitCommit,
  Pencil,
  PlusCircle,
  RefreshCw,
  Trash2,
} from "lucide-react";
import Card from "../../Card/Card.jsx";
import Button from "../../Button/Button.jsx";
import Spinner from "../../Spinner/Spinner.jsx";
import { EmptyState, ErrorState } from "../../StatePanel/StatePanel.jsx";
import { taskService } from "../../../services/taskService.js";
import { apiErrorMessage } from "../../../utils/apiErrorMessage.js";
import { formatAbsoluteDate, formatActivityTime } from "../../../utils/date.js";
import "./TaskActivity.css";

const ACTIVITY_ICONS = {
  created: PlusCircle,
  updated: Pencil,
  status_changed: RefreshCw,
  priority_changed: AlertCircle,
  deadline_changed: CalendarClock,
  completed: CheckCircle2,
  dependency_added: GitCommit,
  dependency_removed: Trash2,
};

function TaskActivity({ taskId, refreshKey = 0 }) {
  const [activities, setActivities] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");

  const loadActivities = useCallback(async () => {
    setIsLoading(true);
    setError("");
    try {
      const data = await taskService.getActivities(taskId);
      setActivities(data || []);
    } catch (err) {
      setError(apiErrorMessage(err, "Failed to load activity history."));
    } finally {
      setIsLoading(false);
    }
  }, [taskId]);

  useEffect(() => {
    loadActivities();
  }, [loadActivities, refreshKey]);

  return (
    <Card className="task-activity">
      <div className="task-activity__header">
        <h2 className="task-activity__title">
          <Activity size={18} aria-hidden="true" />
          Activity History
        </h2>
      </div>

      {isLoading && (
        <div style={{ display: "flex", justifyContent: "center", padding: "var(--space-6) 0" }}>
          <Spinner size="md" label="Loading activity" />
        </div>
      )}

      {error && !isLoading && (
        <ErrorState
          title="Couldn't load activities"
          description={error}
          action={
            <Button variant="secondary" onClick={loadActivities}>
              Try again
            </Button>
          }
        />
      )}

      {!isLoading && !error && activities.length === 0 && (
        <EmptyState
          icon={<Activity size={20} aria-hidden="true" />}
          title="No activity recorded yet"
          description="Actions performed on this task will appear here."
        />
      )}

      {!isLoading && !error && activities.length > 0 && (
        <div className="task-activity__timeline" role="feed" aria-label="Task activity timeline">
          {activities.map((act) => {
            const Icon = ACTIVITY_ICONS[act.activity_type] || Activity;
            return (
              <div
                key={act.id}
                className={`task-activity__item task-activity__item--${act.activity_type}`}
              >
                <div className="task-activity__icon-wrapper" aria-hidden="true">
                  <Icon size={14} />
                </div>
                <div className="task-activity__content">
                  <div className="task-activity__row">
                    <p className="task-activity__desc">{act.description}</p>
                    <time
                      className="task-activity__time"
                      dateTime={act.created_at}
                      title={formatAbsoluteDate(act.created_at)}
                    >
                      {formatActivityTime(act.created_at)}
                    </time>
                  </div>
                  {act.metadata && Object.keys(act.metadata).length > 0 && (
                    <div className="task-activity__meta">
                      {act.metadata.old_status && act.metadata.new_status && (
                        <span className="task-activity__meta-tag">
                          {act.metadata.old_status} → {act.metadata.new_status}
                        </span>
                      )}
                      {act.metadata.old_priority && act.metadata.new_priority && (
                        <span className="task-activity__meta-tag">
                          {act.metadata.old_priority} → {act.metadata.new_priority}
                        </span>
                      )}
                      {act.metadata.dependency_task_title && (
                        <span className="task-activity__meta-tag">
                          Task: {act.metadata.dependency_task_title}
                        </span>
                      )}
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </Card>
  );
}

export default TaskActivity;
