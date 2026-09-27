import { useState } from "react";
import {
  AlertCircle,
  AlertTriangle,
  CalendarClock,
  CheckCircle2,
  Clock,
  Layers,
  LayoutList,
  PauseCircle,
  RotateCw,
  Sparkles,
  TrendingUp,
} from "lucide-react";
import Card from "../../Card/Card.jsx";
import Badge from "../../Badge/Badge.jsx";
import Button from "../../Button/Button.jsx";
import Spinner from "../../Spinner/Spinner.jsx";
import { EmptyState, ErrorState } from "../../StatePanel/StatePanel.jsx";
import { projectService } from "../../../services/projectService.js";
import { apiErrorMessage } from "../../../utils/apiErrorMessage.js";
import "./ProjectProgressIntelligence.css";

const TYPE_CONFIG = {
  priority: {
    label: "Priority",
    icon: AlertTriangle,
    className: "project-intel__card--priority",
    iconClassName: "project-intel__icon--priority",
    prefix: "⚠",
  },
  deadline: {
    label: "Deadline",
    icon: CalendarClock,
    className: "project-intel__card--deadline",
    iconClassName: "project-intel__icon--deadline",
    prefix: "⚠",
  },
  bottleneck: {
    label: "Bottleneck",
    icon: AlertCircle,
    className: "project-intel__card--bottleneck",
    iconClassName: "project-intel__icon--bottleneck",
    prefix: "⚠",
  },
  workload: {
    label: "Workload",
    icon: LayoutList,
    className: "project-intel__card--workload",
    iconClassName: "project-intel__icon--workload",
    prefix: "●",
  },
  positive: {
    label: "Positive",
    icon: CheckCircle2,
    className: "project-intel__card--positive",
    iconClassName: "project-intel__icon--positive",
    prefix: "✓",
  },
  progress: {
    label: "Progress",
    icon: TrendingUp,
    className: "project-intel__card--progress",
    iconClassName: "project-intel__icon--progress",
    prefix: "📈",
  },
};

const SEVERITY_CONFIG = {
  high: { variant: "danger", label: "High" },
  medium: { variant: "ai", label: "Medium" },
  low: { variant: "neutral", label: "Low" },
  info: { variant: "neutral", label: "Info" },
};

export default function ProjectProgressIntelligence({
  projectId,
  totalTasks = 0,
  completedTasks = 0,
  className = "",
}) {
  const [data, setData] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");
  const [hasAnalyzed, setHasAnalyzed] = useState(false);

  async function handleAnalyze() {
    if (isLoading) return;

    // If project has 0 tasks, show empty state immediately without calling AI
    if (totalTasks === 0) {
      setData({
        project_summary: "No project progress data available yet. Add tasks to generate project intelligence.",
        overall_progress: 0,
        insights: [],
      });
      setHasAnalyzed(true);
      setError("");
      return;
    }

    setIsLoading(true);
    setError("");

    try {
      const res = await projectService.getProgressInsights(projectId);
      setData(res);
      setHasAnalyzed(true);
    } catch (err) {
      setError(
        apiErrorMessage(
          err,
          "Unable to generate project intelligence at this time. Please try again."
        )
      );
    } finally {
      setIsLoading(false);
    }
  }

  const isEmpty =
    hasAnalyzed &&
    (totalTasks === 0 ||
      (data &&
        (!data.insights || data.insights.length === 0) &&
        data.overall_progress === 0 &&
        data.project_summary?.toLowerCase().includes("no project progress data")));

  return (
    <Card className={`project-intel ${className}`}>
      <div className="project-intel__header">
        <div className="project-intel__title-group">
          <div className="project-intel__heading-row">
            <Sparkles size={18} className="project-intel__sparkle" aria-hidden="true" />
            <h3 className="project-intel__heading">AI Project Intelligence</h3>
          </div>
          <p className="project-intel__subheading">
            Evidence-based observations of project progress, bottlenecks, priorities, and workload
          </p>
        </div>

        <Button
          variant={hasAnalyzed ? "secondary" : "primary"}
          size="sm"
          onClick={handleAnalyze}
          disabled={isLoading}
          aria-label={
            isLoading
              ? "Analyzing project progress..."
              : hasAnalyzed
              ? "Re-analyze project"
              : "Analyze project"
          }
        >
          {isLoading ? (
            <>
              <Spinner size="xs" label="" />
              <span>Analyzing...</span>
            </>
          ) : hasAnalyzed ? (
            <>
              <RotateCw size={14} aria-hidden="true" />
              <span>Re-analyze</span>
            </>
          ) : (
            <>
              <Sparkles size={14} aria-hidden="true" />
              <span>✨ Analyze Project</span>
            </>
          )}
        </Button>
      </div>

      {isLoading && (
        <div className="project-intel__loading" role="status" aria-live="polite">
          <Spinner size="md" label="Analyzing project progress..." />
          <p className="project-intel__loading-title">Analyzing project progress...</p>
          <span className="project-intel__loading-desc">
            Evaluating task completion rates, phases, high-priority work, deadlines, and bottlenecks
          </span>
        </div>
      )}

      {error && !isLoading && (
        <div className="project-intel__error">
          <ErrorState
            title="Unable to analyze project progress"
            description={error}
            action={
              <Button variant="secondary" size="sm" onClick={handleAnalyze}>
                <RotateCw size={14} aria-hidden="true" />
                Retry analysis
              </Button>
            }
          />
        </div>
      )}

      {!isLoading && !error && !hasAnalyzed && (
        <div className="project-intel__initial">
          <div className="project-intel__initial-inner">
            <Sparkles size={24} className="project-intel__initial-sparkle" aria-hidden="true" />
            <div className="project-intel__initial-copy">
              <h4>Analyze Project Progress with AI</h4>
              <p>
                Get evidence-based intelligence on overall project completion, incomplete high-priority
                work, approaching deadlines, stalled tasks, and workload distribution.
              </p>
            </div>
            <Button variant="primary" size="sm" onClick={handleAnalyze}>
              <Sparkles size={14} aria-hidden="true" />
              ✨ Analyze Project
            </Button>
          </div>
        </div>
      )}

      {!isLoading && !error && isEmpty && (
        <div className="project-intel__empty">
          <EmptyState
            icon={<Sparkles size={24} aria-hidden="true" />}
            title="No project progress data available yet."
            description="Add tasks to generate project intelligence."
          />
        </div>
      )}

      {!isLoading && !error && hasAnalyzed && !isEmpty && data && (
        <div className="project-intel__content">
          {/* Key Metrics Ribbon */}
          <div className="project-intel__metrics-ribbon">
            <div className="project-intel__metric-item">
              <span className="project-intel__metric-value project-intel__metric-value--progress">
                {data.overall_progress}%
              </span>
              <span className="project-intel__metric-label">complete</span>
            </div>

            {totalTasks > 0 && (
              <div className="project-intel__metric-item">
                <span className="project-intel__metric-value">
                  {completedTasks} / {totalTasks}
                </span>
                <span className="project-intel__metric-label">tasks completed</span>
              </div>
            )}
          </div>

          {/* Project Summary */}
          {data.project_summary && (
            <div className="project-intel__summary-box">
              <span className="project-intel__summary-tag">Key observations:</span>
              <p className="project-intel__summary-text">{data.project_summary}</p>
            </div>
          )}

          {/* Insight Cards Grid */}
          {data.insights && data.insights.length > 0 && (
            <div className="project-intel__grid">
              {data.insights.map((item, idx) => {
                const conf = TYPE_CONFIG[item.type] || TYPE_CONFIG.progress;
                const Icon = conf.icon;
                const sev = SEVERITY_CONFIG[item.severity] || SEVERITY_CONFIG.info;

                return (
                  <div key={idx} className={`project-intel__card ${conf.className}`}>
                    <div className="project-intel__card-header">
                      <div className="project-intel__card-meta">
                        <Icon size={15} className={`project-intel__card-icon ${conf.iconClassName}`} aria-hidden="true" />
                        <span className="project-intel__card-type">{conf.label}</span>
                      </div>
                      <Badge variant={sev.variant}>{sev.label}</Badge>
                    </div>

                    <h4 className="project-intel__card-title">{item.title}</h4>
                    <p className="project-intel__card-desc">{item.description}</p>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}
    </Card>
  );
}
