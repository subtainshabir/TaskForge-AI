import { useState } from "react";
import {
  AlertCircle,
  AlertTriangle,
  ArrowRight,
  CheckCircle2,
  ChevronRight,
  Edit3,
  HelpCircle,
  Lightbulb,
  RefreshCw,
  Sparkles,
  X,
} from "lucide-react";
import Card from "../../Card/Card.jsx";
import Button from "../../Button/Button.jsx";
import Spinner from "../../Spinner/Spinner.jsx";
import Badge from "../../Badge/Badge.jsx";
import { taskService } from "../../../services/taskService.js";
import { apiErrorMessage } from "../../../utils/apiErrorMessage.js";
import "./TaskAIQuality.css";

function getScoreTier(score) {
  if (score < 40) {
    return {
      label: "Needs significant clarification",
      badgeVariant: "danger",
      barClass: "task-ai-quality__bar--danger",
    };
  }
  if (score < 60) {
    return {
      label: "Needs improvement",
      badgeVariant: "accent",
      barClass: "task-ai-quality__bar--accent",
    };
  }
  if (score < 80) {
    return {
      label: "Reasonably defined",
      badgeVariant: "ai",
      barClass: "task-ai-quality__bar--ai",
    };
  }
  return {
    label: "Well defined",
    badgeVariant: "success",
    barClass: "task-ai-quality__bar--success",
  };
}

function formatDimensionName(name) {
  if (!name) return "";
  return name.charAt(0).toUpperCase() + name.slice(1);
}

function TaskAIQuality({ task, onEditTask, onRegenerateTask }) {
  const [quality, setQuality] = useState(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [error, setError] = useState("");

  const handleAnalyze = async () => {
    if (isAnalyzing) return;
    setIsAnalyzing(true);
    setError("");
    try {
      const data = await taskService.analyzeQualityWithAI(task.id);
      setQuality(data);
    } catch (err) {
      setError(
        apiErrorMessage(
          err,
          "Failed to evaluate task quality with AI. Please check your connection and try again."
        )
      );
    } finally {
      setIsAnalyzing(false);
    }
  };

  const tier = quality ? getScoreTier(quality.overall_score) : null;

  return (
    <Card className={`task-ai-quality ${quality ? "task-ai-quality--active" : ""}`}>
      <div className="task-ai-quality__header">
        <h2 className="task-ai-quality__title">
          <Sparkles size={18} className="task-ai-quality__sparkle-icon" aria-hidden="true" />
          AI Task Quality
        </h2>
        {quality && (
          <Button
            variant="secondary"
            size="sm"
            disabled={isAnalyzing}
            onClick={handleAnalyze}
            aria-label="Re-analyze task quality"
          >
            <RefreshCw size={14} aria-hidden="true" />
            Re-analyze
          </Button>
        )}
      </div>

      {error && (
        <div className="task-ai-quality__error" role="alert">
          <div className="task-ai-quality__error-content">
            <AlertCircle size={16} aria-hidden="true" />
            <span>{error}</span>
          </div>
          <div className="task-ai-quality__error-actions">
            <Button variant="secondary" size="sm" onClick={handleAnalyze}>
              Try again
            </Button>
            <button
              type="button"
              className="task-ai-quality__close-btn"
              onClick={() => setError("")}
              aria-label="Dismiss error"
            >
              <X size={14} aria-hidden="true" />
            </button>
          </div>
        </div>
      )}

      {isAnalyzing && (
        <div className="task-ai-quality__loading-state" aria-live="polite">
          <Spinner size="lg" label="Analyzing task quality" />
          <p className="task-ai-quality__loading-title">Analyzing task...</p>
          <p className="task-ai-quality__loading-subtext">
            Evaluating clarity, specificity, actionability, completeness, and context...
          </p>
        </div>
      )}

      {!isAnalyzing && !quality && (
        <div className="task-ai-quality__empty-state">
          <p className="task-ai-quality__empty-text">
            Assess whether this task is sufficiently clear, specific, actionable, and complete to prevent scope ambiguity and missed requirements.
          </p>
          <Button variant="secondary" onClick={handleAnalyze}>
            <Sparkles size={14} aria-hidden="true" />
            Analyze Task Quality
          </Button>
        </div>
      )}

      {!isAnalyzing && quality && (
        <div className="task-ai-quality__content">
          <div className="task-ai-quality__score-banner">
            <div className="task-ai-quality__score-metric">
              <span className="task-ai-quality__score-number">{quality.overall_score}</span>
              <span className="task-ai-quality__score-max">/100</span>
            </div>
            <div className="task-ai-quality__score-details">
              <Badge variant={tier.badgeVariant} className="task-ai-quality__tier-badge">
                {tier.label}
              </Badge>
              <p className="task-ai-quality__summary">{quality.summary}</p>
            </div>
          </div>

          {quality.dimensions && quality.dimensions.length > 0 && (
            <div className="task-ai-quality__dimensions-section">
              <h3 className="task-ai-quality__section-heading">Quality Dimensions</h3>
              <div className="task-ai-quality__dimensions-grid">
                {quality.dimensions.map((dim, idx) => {
                  const dimTier = getScoreTier(dim.score);
                  return (
                    <div key={idx} className="task-ai-quality__dimension-item">
                      <div className="task-ai-quality__dim-header">
                        <span className="task-ai-quality__dim-name">
                          {formatDimensionName(dim.name)}
                        </span>
                        <span className="task-ai-quality__dim-score">{dim.score}</span>
                      </div>
                      <div className="task-ai-quality__progress-track" aria-hidden="true">
                        <div
                          className={`task-ai-quality__progress-fill ${dimTier.barClass}`}
                          style={{ width: `${dim.score}%` }}
                        />
                      </div>
                      {dim.explanation && (
                        <p className="task-ai-quality__dim-explanation">{dim.explanation}</p>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {quality.issues && quality.issues.length > 0 && (
            <div className="task-ai-quality__section">
              <h3 className="task-ai-quality__section-heading task-ai-quality__section-heading--issues">
                <AlertTriangle size={15} aria-hidden="true" />
                Issues
              </h3>
              <div className="task-ai-quality__issues-list">
                {quality.issues.map((issue, idx) => (
                  <div key={idx} className="task-ai-quality__issue-card">
                    <div className="task-ai-quality__issue-header">
                      <span className="task-ai-quality__issue-title">
                        {issue.title}
                      </span>
                      {issue.severity && (
                        <Badge
                          variant={
                            issue.severity === "high"
                              ? "danger"
                              : issue.severity === "medium"
                              ? "accent"
                              : "neutral"
                          }
                          className="task-ai-quality__issue-severity"
                        >
                          {issue.severity} severity
                        </Badge>
                      )}
                    </div>
                    {issue.description && (
                      <p className="task-ai-quality__issue-desc">{issue.description}</p>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {quality.suggestions && quality.suggestions.length > 0 && (
            <div className="task-ai-quality__section">
              <h3 className="task-ai-quality__section-heading task-ai-quality__section-heading--suggestions">
                <Lightbulb size={15} aria-hidden="true" />
                Suggestions
              </h3>
              <ul className="task-ai-quality__suggestions-list">
                {quality.suggestions.map((sug, idx) => (
                  <li key={idx} className="task-ai-quality__suggestion-item">
                    <div className="task-ai-quality__suggestion-bullet" aria-hidden="true">•</div>
                    <div className="task-ai-quality__suggestion-content">
                      <strong className="task-ai-quality__suggestion-title">{sug.title}</strong>
                      {sug.description && (
                        <span className="task-ai-quality__suggestion-desc"> — {sug.description}</span>
                      )}
                    </div>
                  </li>
                ))}
              </ul>
            </div>
          )}

          <div className="task-ai-quality__actions">
            {onRegenerateTask && (
              <Button
                variant="primary"
                onClick={onRegenerateTask}
                id="regenerate-task-button"
              >
                <Sparkles size={14} aria-hidden="true" />
                Regenerate with AI
              </Button>
            )}
            {onEditTask && (
              <Button
                variant="secondary"
                onClick={onEditTask}
                id="improve-task-button"
              >
                <Edit3 size={14} aria-hidden="true" />
                Edit Task
              </Button>
            )}
            <Button
              variant="secondary"
              onClick={() => setQuality(null)}
              id="dismiss-quality-button"
            >
              Dismiss
            </Button>
          </div>

          <p className="task-ai-quality__disclaimer">
            This quality score is an AI-generated assessment to help clarify your task definition, not an objective scientific measurement.
          </p>
        </div>
      )}
    </Card>
  );
}

export default TaskAIQuality;
