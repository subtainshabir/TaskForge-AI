import { useState } from "react";
import {
  AlertCircle,
  AlertTriangle,
  CalendarClock,
  CheckCircle2,
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
import { analyticsService } from "../../../services/analyticsService.js";
import { apiErrorMessage } from "../../../utils/apiErrorMessage.js";
import "./ProgressInsights.css";

const TYPE_CONFIG = {
  bottleneck: {
    label: "Bottleneck",
    icon: AlertTriangle,
    className: "progress-insights__card--bottleneck",
    iconClassName: "progress-insights__icon--bottleneck",
  },
  stalled: {
    label: "Stalled",
    icon: PauseCircle,
    className: "progress-insights__card--stalled",
    iconClassName: "progress-insights__icon--stalled",
  },
  deadline: {
    label: "Deadline",
    icon: CalendarClock,
    className: "progress-insights__card--deadline",
    iconClassName: "progress-insights__icon--deadline",
  },
  positive: {
    label: "Positive",
    icon: CheckCircle2,
    className: "progress-insights__card--positive",
    iconClassName: "progress-insights__icon--positive",
  },
  progress: {
    label: "Progress",
    icon: TrendingUp,
    className: "progress-insights__card--progress",
    iconClassName: "progress-insights__icon--progress",
  },
};

const SEVERITY_CONFIG = {
  high: { variant: "danger", label: "High priority" },
  medium: { variant: "ai", label: "Medium priority" },
  low: { variant: "neutral", label: "Low priority" },
  info: { variant: "neutral", label: "Info" },
};

export default function ProgressInsights({ projectId = null, className = "" }) {
  const [data, setData] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");
  const [hasAnalyzed, setHasAnalyzed] = useState(false);

  async function handleAnalyze() {
    if (isLoading) return;
    setIsLoading(true);
    setError("");

    try {
      const params = projectId ? { project_id: projectId } : {};
      const res = await analyticsService.getInsights(params);
      setData(res);
      setHasAnalyzed(true);
    } catch (err) {
      setError(
        apiErrorMessage(
          err,
          "Unable to generate progress insights at this time. Please try again."
        )
      );
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <Card className={`progress-insights ${className}`}>
      <div className="progress-insights__header">
        <div className="progress-insights__title-wrap">
          <div className="progress-insights__title-row">
            <Sparkles size={18} className="progress-insights__sparkle-icon" aria-hidden="true" />
            <h3 className="progress-insights__title">AI Progress Insights</h3>
          </div>
          <p className="progress-insights__subtitle">
            Evidence-based observations of current progress, stalled work, and focus areas
          </p>
        </div>

        <Button
          variant={hasAnalyzed ? "secondary" : "primary"}
          size="sm"
          onClick={handleAnalyze}
          disabled={isLoading}
          aria-label={isLoading ? "Analyzing progress..." : hasAnalyzed ? "Re-analyze progress" : "Analyze progress"}
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
              <span>Analyze Progress</span>
            </>
          )}
        </Button>
      </div>

      {isLoading && (
        <div className="progress-insights__loading-box" role="status" aria-live="polite">
          <Spinner size="md" label="Analyzing your progress..." />
          <p className="progress-insights__loading-text">
            Analyzing your progress...
          </p>
          <span className="progress-insights__loading-subtext">
            Evaluating task completion rates, phase statuses, priorities, and deadlines
          </span>
        </div>
      )}

      {error && !isLoading && (
        <div className="progress-insights__error-box">
          <ErrorState
            title="Unable to load progress insights"
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
        <div className="progress-insights__initial-box">
          <div className="progress-insights__initial-content">
            <Sparkles size={28} className="progress-insights__initial-icon" aria-hidden="true" />
            <div className="progress-insights__initial-text">
              <h4>Get an intelligent analysis of your progress</h4>
              <p>
                TaskForge AI inspects your actual task and phase completion data to highlight
                bottlenecks, stalled active tasks, approaching deadlines, and milestones.
              </p>
            </div>
            <Button variant="primary" size="sm" onClick={handleAnalyze}>
              <Sparkles size={14} aria-hidden="true" />
              Analyze Progress
            </Button>
          </div>
        </div>
      )}

      {!isLoading && !error && hasAnalyzed && data && (
        <div className="progress-insights__results">
          {data.summary && (
            <div className="progress-insights__summary-banner">
              <span className="progress-insights__summary-label">Summary</span>
              <p className="progress-insights__summary-text">{data.summary}</p>
            </div>
          )}

          {data.insights && data.insights.length > 0 ? (
            <div className="progress-insights__grid">
              {data.insights.map((item, index) => {
                const conf = TYPE_CONFIG[item.type] || TYPE_CONFIG.progress;
                const Icon = conf.icon;
                const sev = SEVERITY_CONFIG[item.severity] || SEVERITY_CONFIG.info;

                return (
                  <div
                    key={index}
                    className={`progress-insights__item-card ${conf.className}`}
                  >
                    <div className="progress-insights__item-header">
                      <div className="progress-insights__item-meta">
                        <Icon size={16} className={`progress-insights__item-icon ${conf.iconClassName}`} aria-hidden="true" />
                        <span className="progress-insights__item-type-label">{conf.label}</span>
                      </div>
                      <Badge variant={sev.variant}>
                        {sev.label}
                      </Badge>
                    </div>

                    <h4 className="progress-insights__item-title">{item.title}</h4>
                    <p className="progress-insights__item-desc">{item.description}</p>
                  </div>
                );
              })}
            </div>
          ) : (
            <EmptyState
              icon={<Sparkles size={22} aria-hidden="true" />}
              title="Not enough task data for meaningful AI insights yet."
              description="Add tasks and complete phases in your projects to unlock automated progress observations."
            />
          )}
        </div>
      )}
    </Card>
  );
}
