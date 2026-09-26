import { Link } from "react-router-dom";
import {
  ArrowRight,
  BarChart3,
  CheckCircle2,
  Clock,
  FolderKanban,
  RotateCw,
  TrendingUp,
} from "lucide-react";
import Card from "../../Card/Card.jsx";
import Badge from "../../Badge/Badge.jsx";
import Button from "../../Button/Button.jsx";
import { EmptyState, ErrorState } from "../../StatePanel/StatePanel.jsx";
import ProgressInsights from "../ProgressInsights/ProgressInsights.jsx";
import "./ProgressAnalytics.css";

export default function ProgressAnalytics({
  data,
  isLoading,
  error,
  onRefresh,
  projectId = null,
}) {
  if (isLoading && !data) {
    return (
      <section className="progress-analytics" aria-label="Loading progress analytics">
        <div className="progress-analytics__header">
          <div>
            <h2 className="progress-analytics__title">Progress Analytics</h2>
            <p className="progress-analytics__subtitle">
              Real-time breakdown of workspace tasks and project completion
            </p>
          </div>
        </div>
        <div className="progress-analytics__grid">
          <Card className="progress-analytics__skeleton-card">
            <div className="progress-analytics__skeleton-line" style={{ width: "40%", height: "20px" }} />
            <div className="progress-analytics__skeleton-line" style={{ width: "70%", height: "36px", marginTop: "12px" }} />
            <div className="progress-analytics__skeleton-line" style={{ width: "100%", height: "12px", marginTop: "16px" }} />
            <div className="progress-analytics__skeleton-line" style={{ width: "85%", height: "16px", marginTop: "12px" }} />
          </Card>
          <Card className="progress-analytics__skeleton-card">
            <div className="progress-analytics__skeleton-line" style={{ width: "50%", height: "20px" }} />
            <div className="progress-analytics__skeleton-line" style={{ width: "100%", height: "100px", marginTop: "16px" }} />
          </Card>
        </div>
      </section>
    );
  }

  if (error && !data) {
    return (
      <section className="progress-analytics" aria-label="Progress analytics error">
        <Card>
          <ErrorState
            title="Unable to load progress analytics."
            description="We encountered an issue fetching the latest workspace analytics. Please try again."
            action={
              onRefresh ? (
                <Button variant="secondary" onClick={onRefresh}>
                  <RotateCw size={14} aria-hidden="true" />
                  Retry
                </Button>
              ) : null
            }
          />
        </Card>
      </section>
    );
  }

  const overview = data?.overview || {
    total_tasks: 0,
    completed_tasks: 0,
    in_progress_tasks: 0,
    todo_tasks: 0,
    blocked_tasks: 0,
    average_progress: 0,
  };

  const statusBreakdown = data?.status_breakdown || {
    completed: overview.completed_tasks,
    in_progress: overview.in_progress_tasks,
    todo: overview.todo_tasks,
    blocked: overview.blocked_tasks,
  };

  const distribution = data?.progress_distribution;
  const buckets = distribution?.buckets || [];
  const projects = data?.projects || [];

  if (overview.total_tasks === 0) {
    return (
      <section className="progress-analytics" aria-label="Progress analytics">
        <div className="progress-analytics__header">
          <div>
            <h2 className="progress-analytics__title">Progress Analytics</h2>
            <p className="progress-analytics__subtitle">
              Real-time breakdown of workspace tasks and project completion
            </p>
          </div>
          {onRefresh && (
            <Button
              variant="ghost"
              size="sm"
              onClick={onRefresh}
              disabled={isLoading}
              title="Refresh analytics"
            >
              <RotateCw size={14} className={isLoading ? "progress-analytics__spin" : ""} />
              Refresh
            </Button>
          )}
        </div>
        <Card>
          <EmptyState
            icon={<TrendingUp size={24} aria-hidden="true" />}
            title="No task progress data yet."
            description="Create your first task and start tracking progress."
          />
        </Card>
      </section>
    );
  }

  // Calculate segment widths for status breakdown bar
  const totalTasks = overview.total_tasks;
  const completedPct = totalTasks ? (statusBreakdown.completed / totalTasks) * 100 : 0;
  const inProgressPct = totalTasks ? (statusBreakdown.in_progress / totalTasks) * 100 : 0;
  const todoPct = totalTasks ? (statusBreakdown.todo / totalTasks) * 100 : 0;
  const blockedPct = totalTasks ? ((statusBreakdown.blocked || 0) / totalTasks) * 100 : 0;

  // Max bucket count for scaling distribution chart
  const maxBucketCount = Math.max(...buckets.map((b) => b.count), 1);

  return (
    <section className="progress-analytics" aria-labelledby="progress-analytics-heading">
      <div className="progress-analytics__header">
        <div>
          <h2 id="progress-analytics-heading" className="progress-analytics__title">
            Progress Analytics
          </h2>
          <p className="progress-analytics__subtitle">
            Real-time breakdown of workspace tasks and project completion
          </p>
        </div>
        {onRefresh && (
          <Button
            variant="ghost"
            size="sm"
            onClick={onRefresh}
            disabled={isLoading}
            title="Refresh analytics"
          >
            <RotateCw size={14} className={isLoading ? "progress-analytics__spin" : ""} />
            Refresh
          </Button>
        )}
      </div>

      <div className="progress-analytics__grid">
        {/* Card 1: Overview & Average Progress */}
        <Card className="progress-analytics__card">
          <div className="progress-analytics__card-header">
            <h3 className="progress-analytics__card-title">
              <TrendingUp size={16} aria-hidden="true" className="progress-analytics__icon" />
              Progress Overview
            </h3>
          </div>

          <div className="progress-analytics__overview-stats">
            <div className="progress-analytics__stat-item">
              <span className="progress-analytics__stat-label">Total Tasks</span>
              <span className="progress-analytics__stat-value">{overview.total_tasks}</span>
            </div>
            <div className="progress-analytics__stat-item">
              <span className="progress-analytics__stat-label">Completed</span>
              <span className="progress-analytics__stat-value progress-analytics__stat-value--completed">
                {overview.completed_tasks}
              </span>
            </div>
            <div className="progress-analytics__stat-item">
              <span className="progress-analytics__stat-label">In Progress</span>
              <span className="progress-analytics__stat-value progress-analytics__stat-value--in-progress">
                {overview.in_progress_tasks}
              </span>
            </div>
            <div className="progress-analytics__stat-item">
              <span className="progress-analytics__stat-label">Not Started</span>
              <span className="progress-analytics__stat-value">{overview.todo_tasks}</span>
            </div>
          </div>

          <div className="progress-analytics__avg-box">
            <div className="progress-analytics__avg-header">
              <span className="progress-analytics__avg-label">Average Task Progress</span>
              <span className="progress-analytics__avg-value">{overview.average_progress}%</span>
            </div>
            <div
              className="progress-analytics__progress-track"
              role="progressbar"
              aria-valuenow={overview.average_progress}
              aria-valuemin="0"
              aria-valuemax="100"
              aria-label="Average task progress"
            >
              <div
                className="progress-analytics__progress-fill"
                style={{ width: `${overview.average_progress}%` }}
              />
            </div>
          </div>

          <div className="progress-analytics__status-section">
            <h4 className="progress-analytics__subheading">Task Status Breakdown</h4>
            <div className="progress-analytics__stacked-bar" role="img" aria-label="Task status breakdown">
              {completedPct > 0 && (
                <div
                  className="progress-analytics__stacked-seg progress-analytics__stacked-seg--completed"
                  style={{ width: `${completedPct}%` }}
                  title={`Completed: ${statusBreakdown.completed} (${Math.round(completedPct)}%)`}
                />
              )}
              {inProgressPct > 0 && (
                <div
                  className="progress-analytics__stacked-seg progress-analytics__stacked-seg--in-progress"
                  style={{ width: `${inProgressPct}%` }}
                  title={`In Progress: ${statusBreakdown.in_progress} (${Math.round(inProgressPct)}%)`}
                />
              )}
              {todoPct > 0 && (
                <div
                  className="progress-analytics__stacked-seg progress-analytics__stacked-seg--todo"
                  style={{ width: `${todoPct}%` }}
                  title={`Todo: ${statusBreakdown.todo} (${Math.round(todoPct)}%)`}
                />
              )}
              {blockedPct > 0 && (
                <div
                  className="progress-analytics__stacked-seg progress-analytics__stacked-seg--blocked"
                  style={{ width: `${blockedPct}%` }}
                  title={`Blocked: ${statusBreakdown.blocked} (${Math.round(blockedPct)}%)`}
                />
              )}
            </div>

            <div className="progress-analytics__legend">
              <div className="progress-analytics__legend-item">
                <span className="progress-analytics__legend-dot progress-analytics__legend-dot--completed" />
                <span className="progress-analytics__legend-label">Completed:</span>
                <span className="progress-analytics__legend-val">{statusBreakdown.completed}</span>
              </div>
              <div className="progress-analytics__legend-item">
                <span className="progress-analytics__legend-dot progress-analytics__legend-dot--in-progress" />
                <span className="progress-analytics__legend-label">In Progress:</span>
                <span className="progress-analytics__legend-val">{statusBreakdown.in_progress}</span>
              </div>
              <div className="progress-analytics__legend-item">
                <span className="progress-analytics__legend-dot progress-analytics__legend-dot--todo" />
                <span className="progress-analytics__legend-label">Todo:</span>
                <span className="progress-analytics__legend-val">{statusBreakdown.todo}</span>
              </div>
              {statusBreakdown.blocked > 0 && (
                <div className="progress-analytics__legend-item">
                  <span className="progress-analytics__legend-dot progress-analytics__legend-dot--blocked" />
                  <span className="progress-analytics__legend-label">Blocked:</span>
                  <span className="progress-analytics__legend-val">{statusBreakdown.blocked}</span>
                </div>
              )}
            </div>
          </div>
        </Card>

        {/* Card 2: Progress Distribution */}
        <Card className="progress-analytics__card">
          <div className="progress-analytics__card-header">
            <h3 className="progress-analytics__card-title">
              <BarChart3 size={16} aria-hidden="true" className="progress-analytics__icon" />
              Task Progress Distribution
            </h3>
          </div>

          <div className="progress-analytics__chart-container">
            <div className="progress-analytics__bar-chart">
              {buckets.map((b) => {
                const heightPct = Math.round((b.count / maxBucketCount) * 100);
                return (
                  <div key={b.key} className="progress-analytics__bar-col">
                    <span className="progress-analytics__bar-count">{b.count}</span>
                    <div className="progress-analytics__bar-track">
                      <div
                        className="progress-analytics__bar-fill"
                        style={{ height: `${heightPct}%` }}
                        title={`${b.label}: ${b.count} tasks (${b.percentage}%)`}
                      />
                    </div>
                    <span className="progress-analytics__bar-label">{b.label}</span>
                  </div>
                );
              })}
            </div>
          </div>

          <div className="progress-analytics__dist-summary">
            {buckets.map((b) => (
              <div key={b.key} className="progress-analytics__dist-row">
                <span className="progress-analytics__dist-range">{b.label}</span>
                <div className="progress-analytics__dist-bar-track">
                  <div
                    className="progress-analytics__dist-bar-fill"
                    style={{ width: `${b.percentage}%` }}
                  />
                </div>
                <span className="progress-analytics__dist-count">
                  {b.count} {b.count === 1 ? "task" : "tasks"}
                </span>
                <span className="progress-analytics__dist-pct">({b.percentage}%)</span>
              </div>
            ))}
          </div>
        </Card>
      </div>

      {/* Projects Progress Summary */}
      {projects.length > 0 && (
        <Card className="progress-analytics__projects-card">
          <div className="progress-analytics__card-header">
            <h3 className="progress-analytics__card-title">
              <FolderKanban size={16} aria-hidden="true" className="progress-analytics__icon" />
              Project Progress Overview
            </h3>
            <span className="progress-analytics__card-hint">
              Sorted by unfinished work
            </span>
          </div>

          <div className="progress-analytics__projects-list">
            {projects.map((proj) => (
              <div key={proj.id} className="progress-analytics__proj-item">
                <div className="progress-analytics__proj-main">
                  <div className="progress-analytics__proj-title-row">
                    <Link
                      to={`/projects/${proj.id}`}
                      className="progress-analytics__proj-name"
                    >
                      {proj.name}
                    </Link>
                    <Badge variant={proj.status === "completed" ? "success" : "neutral"}>
                      {proj.status}
                    </Badge>
                  </div>
                  <div className="progress-analytics__proj-meta">
                    <span>
                      {proj.completed_tasks} / {proj.total_tasks} tasks completed
                    </span>
                    {proj.unfinished_tasks > 0 && (
                      <span className="progress-analytics__proj-unfinished">
                        • {proj.unfinished_tasks} unfinished
                      </span>
                    )}
                  </div>
                </div>

                <div className="progress-analytics__proj-progress-col">
                  <div className="progress-analytics__proj-pct-row">
                    <span className="progress-analytics__proj-pct">
                      {proj.average_progress}%
                    </span>
                  </div>
                  <div
                    className="progress-analytics__proj-track"
                    role="progressbar"
                    aria-valuenow={proj.average_progress}
                    aria-valuemin="0"
                    aria-valuemax="100"
                    aria-label={`${proj.name} progress`}
                  >
                    <div
                      className="progress-analytics__proj-fill"
                      style={{ width: `${proj.average_progress}%` }}
                    />
                  </div>
                </div>

                <Link
                  to={`/projects/${proj.id}`}
                  className="progress-analytics__proj-link"
                  aria-label={`View ${proj.name}`}
                >
                  <ArrowRight size={16} aria-hidden="true" />
                </Link>
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* AI Progress Insights (Phase 33) */}
      <ProgressInsights projectId={projectId} />
    </section>
  );
}
