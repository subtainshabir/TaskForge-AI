import { useState } from "react";
import {
  AlertCircle,
  ArrowRight,
  Check,
  CheckCircle2,
  Flame,
  Percent,
  RefreshCw,
  Sparkles,
  X,
} from "lucide-react";
import Card from "../../Card/Card.jsx";
import Button from "../../Button/Button.jsx";
import Spinner from "../../Spinner/Spinner.jsx";
import { taskService } from "../../../services/taskService.js";
import { apiErrorMessage } from "../../../utils/apiErrorMessage.js";
import { TASK_PRIORITY_META } from "../../../utils/taskPriority.js";
import "./TaskAIPriority.css";

function TaskAIPriority({ task, onPriorityApplied }) {
  const [recommendation, setRecommendation] = useState(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [isApplying, setIsApplying] = useState(false);
  const [error, setError] = useState("");
  const [successMessage, setSuccessMessage] = useState("");

  const isCompleted = task?.status === "completed";

  const handleAnalyze = async () => {
    if (isAnalyzing || isCompleted) return;
    setIsAnalyzing(true);
    setError("");
    setSuccessMessage("");
    try {
      const data = await taskService.analyzePriorityWithAI(task.id);
      setRecommendation(data);
    } catch (err) {
      setError(
        apiErrorMessage(
          err,
          "Failed to analyze task priority with AI. Please check your AI configuration and try again."
        )
      );
    } finally {
      setIsAnalyzing(false);
    }
  };

  const handleApply = async () => {
    if (!recommendation || isApplying) return;
    setIsApplying(true);
    setError("");
    try {
      const updated = await taskService.update(task.id, {
        priority: recommendation.recommended_priority,
        source: "ai_priority_recommendation",
      });
      const recMeta = TASK_PRIORITY_META[recommendation.recommended_priority];
      setSuccessMessage(`Priority updated to ${recMeta?.label || recommendation.recommended_priority}`);
      setRecommendation(null);
      if (onPriorityApplied) {
        onPriorityApplied(updated);
      }
    } catch (err) {
      setError(apiErrorMessage(err, "Failed to apply recommended priority."));
    } finally {
      setIsApplying(false);
    }
  };

  const handleDismiss = () => {
    setRecommendation(null);
    setError("");
  };

  const currentPriorityKey = (recommendation?.current_priority || task?.priority || "medium").toLowerCase();
  const recommendedPriorityKey = (recommendation?.recommended_priority || "medium").toLowerCase();

  const currentMeta = TASK_PRIORITY_META[currentPriorityKey] || {
    label: currentPriorityKey,
    badgeVariant: "neutral",
  };
  const recommendedMeta = TASK_PRIORITY_META[recommendedPriorityKey] || {
    label: recommendedPriorityKey,
    badgeVariant: "accent",
  };

  const CurrentIcon = currentMeta.icon || Flame;
  const RecommendedIcon = recommendedMeta.icon || Flame;

  const confidencePercent = recommendation?.confidence != null
    ? Math.round(recommendation.confidence * 100)
    : null;

  const isDifferent = recommendation && recommendation.recommended_priority !== task.priority;

  return (
    <Card className={`task-ai-priority ${recommendation ? "task-ai-priority--active" : ""}`}>
      <div className="task-ai-priority__header">
        <h2 className="task-ai-priority__title">
          <Sparkles size={18} className="task-ai-priority__sparkle-icon" aria-hidden="true" />
          AI Priority Intelligence
        </h2>
        {recommendation && !isCompleted && (
          <Button
            variant="secondary"
            size="sm"
            disabled={isAnalyzing || isApplying}
            onClick={handleAnalyze}
            aria-label="Re-analyze task priority"
          >
            <RefreshCw size={14} aria-hidden="true" />
            Re-analyze
          </Button>
        )}
      </div>

      {isCompleted && (
        <div className="task-ai-priority__completed-notice" role="status">
          <CheckCircle2 size={16} aria-hidden="true" />
          <span>Completed tasks do not require priority analysis.</span>
        </div>
      )}

      {successMessage && (
        <div className="task-ai-priority__success-notice" role="status">
          <div className="task-ai-priority__success-content">
            <CheckCircle2 size={16} aria-hidden="true" />
            <span>{successMessage}</span>
          </div>
          <button
            type="button"
            className="task-ai-priority__close-btn"
            onClick={() => setSuccessMessage("")}
            aria-label="Dismiss message"
          >
            <X size={14} aria-hidden="true" />
          </button>
        </div>
      )}

      {error && (
        <div className="task-ai-priority__error" role="alert">
          <div className="task-ai-priority__error-content">
            <AlertCircle size={16} aria-hidden="true" />
            <span>{error}</span>
          </div>
          <div className="task-ai-priority__error-actions">
            <Button variant="secondary" size="sm" onClick={handleAnalyze}>
              Try again
            </Button>
            <button
              type="button"
              className="task-ai-priority__close-btn"
              onClick={() => setError("")}
              aria-label="Dismiss error"
            >
              <X size={14} aria-hidden="true" />
            </button>
          </div>
        </div>
      )}

      {isAnalyzing && (
        <div className="task-ai-priority__loading-state" aria-live="polite">
          <Spinner size="lg" label="Analyzing task priority" />
          <p className="task-ai-priority__loading-title">Analyzing task priority...</p>
          <p className="task-ai-priority__loading-subtext">
            Evaluating scope, deadlines, downstream blockers, and technical urgency...
          </p>
        </div>
      )}

      {!isAnalyzing && !recommendation && !isCompleted && (
        <div className="task-ai-priority__empty-state">
          <p className="task-ai-priority__empty-text">
            Use AI to evaluate whether this task's current priority (
            <span className="task-ai-priority__highlight">{currentMeta.label}</span>
            ) appropriately matches its deadline, dependency bottlenecks, and technical impact.
          </p>
          <Button variant="secondary" onClick={handleAnalyze}>
            <Sparkles size={14} aria-hidden="true" />
            Analyze Priority with AI
          </Button>
        </div>
      )}

      {!isAnalyzing && recommendation && (
        <div className="task-ai-priority__review">
          <div className="task-ai-priority__comparison">
            <div className="task-ai-priority__badge-box task-ai-priority__badge-box--current">
              <span className="task-ai-priority__box-label">Current Priority</span>
              <div className="task-ai-priority__pill">
                <CurrentIcon size={14} className="task-ai-priority__pill-icon" aria-hidden="true" />
                <span className="task-ai-priority__pill-text">{currentMeta.label}</span>
              </div>
            </div>

            <div className="task-ai-priority__arrow-divider" aria-hidden="true">
              <ArrowRight size={20} />
            </div>

            <div className="task-ai-priority__badge-box task-ai-priority__badge-box--recommended">
              <div className="task-ai-priority__box-header">
                <span className="task-ai-priority__box-label">AI Recommendation</span>
                {isDifferent ? (
                  <span className="task-ai-priority__status-chip task-ai-priority__status-chip--change">
                    Adjustment Suggested
                  </span>
                ) : (
                  <span className="task-ai-priority__status-chip task-ai-priority__status-chip--match">
                    Matches Current
                  </span>
                )}
              </div>
              <div className="task-ai-priority__pill">
                <RecommendedIcon size={14} className="task-ai-priority__pill-icon" aria-hidden="true" />
                <span className="task-ai-priority__pill-text">{recommendedMeta.label}</span>
              </div>
            </div>
          </div>

          {confidencePercent != null && (
            <div className="task-ai-priority__confidence-row">
              <span className="task-ai-priority__confidence-label">Confidence:</span>
              <span className="task-ai-priority__confidence-value">{confidencePercent}%</span>
              <span className="task-ai-priority__confidence-note">
                (AI internal assessment of consistency)
              </span>
            </div>
          )}

          <div className="task-ai-priority__section">
            <h3 className="task-ai-priority__section-title">Why?</h3>
            <p className="task-ai-priority__reasoning">{recommendation.reasoning}</p>
          </div>

          {recommendation.factors && recommendation.factors.length > 0 && (
            <div className="task-ai-priority__section">
              <h3 className="task-ai-priority__section-title">Factors</h3>
              <ul className="task-ai-priority__factors-list">
                {recommendation.factors.map((factor, index) => (
                  <li key={index} className="task-ai-priority__factor-item">
                    <span className="task-ai-priority__factor-bullet" aria-hidden="true">•</span>
                    <span>{factor}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          <div className="task-ai-priority__actions">
            {isDifferent ? (
              <>
                <Button
                  variant="primary"
                  onClick={handleApply}
                  disabled={isApplying}
                  id="apply-ai-priority-button"
                >
                  {isApplying ? (
                    <>
                      <Spinner size="sm" label="Applying" />
                      Applying...
                    </>
                  ) : (
                    <>
                      <Check size={14} aria-hidden="true" />
                      Apply {recommendedMeta.label} Priority
                    </>
                  )}
                </Button>
                <Button
                  variant="secondary"
                  onClick={handleDismiss}
                  disabled={isApplying}
                  id="keep-current-priority-button"
                >
                  Keep {currentMeta.label}
                </Button>
              </>
            ) : (
              <Button
                variant="secondary"
                onClick={handleDismiss}
                disabled={isApplying}
                id="keep-current-priority-button"
              >
                Keep {currentMeta.label}
              </Button>
            )}
          </div>
        </div>
      )}
    </Card>
  );
}

export default TaskAIPriority;
