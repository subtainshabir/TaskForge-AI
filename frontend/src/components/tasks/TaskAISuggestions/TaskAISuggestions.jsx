import { useState, useEffect, useCallback } from "react";
import {
  AlertCircle,
  Check,
  CheckCircle2,
  HelpCircle,
  RefreshCw,
  Sparkles,
  X,
  Plus,
} from "lucide-react";
import Card from "../../Card/Card.jsx";
import Button from "../../Button/Button.jsx";
import Spinner from "../../Spinner/Spinner.jsx";
import Badge from "../../Badge/Badge.jsx";
import { taskService } from "../../../services/taskService.js";
import { apiErrorMessage } from "../../../utils/apiErrorMessage.js";
import { TASK_PRIORITY_META } from "../../../utils/taskPriority.js";
import "./TaskAISuggestions.css";

function TaskAISuggestions({
  projectId,
  taskId = null,
  onTasksCreated,
  onClose,
  autoFetch = false,
  showCloseButton = false,
}) {
  const isTaskLevel = Boolean(taskId);
  const [suggestions, setSuggestions] = useState(null);
  const [selectedIndices, setSelectedIndices] = useState(new Set());
  const [isGenerating, setIsGenerating] = useState(false);
  const [isApplying, setIsApplying] = useState(false);
  const [error, setError] = useState("");
  const [successMessage, setSuccessMessage] = useState("");
  const [newlyCreatedTasks, setNewlyCreatedTasks] = useState([]);

  const handleFetchSuggestions = useCallback(async () => {
    if (isGenerating) return;
    setIsGenerating(true);
    setError("");
    setSuccessMessage("");
    setNewlyCreatedTasks([]);

    try {
      let data;
      if (isTaskLevel) {
        data = await taskService.getTaskRelatedSuggestions(taskId);
      } else {
        data = await taskService.getProjectTaskSuggestions(projectId);
      }

      const list = Array.isArray(data?.suggestions) ? data.suggestions : [];
      setSuggestions(list);
      // By default, select all suggestions so user can easily create or deselect
      setSelectedIndices(new Set(list.map((_, idx) => idx)));
    } catch (err) {
      setError(
        apiErrorMessage(
          err,
          "Failed to generate task suggestions with AI. Please check your AI settings and try again."
        )
      );
    } finally {
      setIsGenerating(false);
    }
  }, [projectId, taskId, isTaskLevel, isGenerating]);

  useEffect(() => {
    if (autoFetch && suggestions === null && !isGenerating && !error) {
      handleFetchSuggestions();
    }
  }, [autoFetch, suggestions, isGenerating, error, handleFetchSuggestions]);

  const handleToggleSelect = (index) => {
    setSelectedIndices((prev) => {
      const next = new Set(prev);
      if (next.has(index)) {
        next.delete(index);
      } else {
        next.add(index);
      }
      return next;
    });
  };

  const handleSelectAll = () => {
    if (!suggestions) return;
    setSelectedIndices(new Set(suggestions.map((_, idx) => idx)));
  };

  const handleDeselectAll = () => {
    setSelectedIndices(new Set());
  };

  const handleApply = async () => {
    if (!suggestions || isApplying || selectedIndices.size === 0) return;

    const chosen = suggestions.filter((_, idx) => selectedIndices.has(idx));
    if (chosen.length === 0) return;

    setIsApplying(true);
    setError("");

    try {
      let created = [];
      if (isTaskLevel) {
        created = await taskService.applyTaskRelatedSuggestions(taskId, chosen);
      } else {
        created = await taskService.applyProjectTaskSuggestions(projectId, chosen);
      }

      const createdList = Array.isArray(created) ? created : [];
      setNewlyCreatedTasks(createdList);
      setSuccessMessage(
        createdList.length > 0
          ? `Successfully created ${createdList.length} task${createdList.length === 1 ? "" : "s"}!`
          : "Selected tasks were already present in the project."
      );
      setSuggestions(null);
      setSelectedIndices(new Set());

      if (onTasksCreated) {
        onTasksCreated(createdList);
      }
    } catch (err) {
      setError(
        apiErrorMessage(
          err,
          "Failed to create selected tasks. Please try again."
        )
      );
    } finally {
      setIsApplying(false);
    }
  };

  const handleCancel = () => {
    setSuggestions(null);
    setSelectedIndices(new Set());
    setError("");
    if (onClose) {
      onClose();
    }
  };

  const selectedCount = selectedIndices.size;
  const totalCount = suggestions ? suggestions.length : 0;

  return (
    <Card className={`task-ai-suggestions ${suggestions ? "task-ai-suggestions--active" : ""}`}>
      <div className="task-ai-suggestions__header">
        <div className="task-ai-suggestions__title-group">
          <h2 className="task-ai-suggestions__title">
            <Sparkles size={18} className="task-ai-suggestions__sparkle-icon" aria-hidden="true" />
            {isTaskLevel ? "AI Related Tasks" : "AI Task Suggestions"}
          </h2>
          <Badge variant="ai">AI Powered</Badge>
        </div>

        <div className="task-ai-suggestions__header-actions">
          {suggestions && !isGenerating && (
            <Button
              variant="secondary"
              size="sm"
              disabled={isGenerating || isApplying}
              onClick={handleFetchSuggestions}
              aria-label="Re-analyze and suggest tasks"
            >
              <RefreshCw size={14} aria-hidden="true" />
              Re-analyze
            </Button>
          )}

          {showCloseButton && onClose && (
            <button
              type="button"
              className="task-ai-suggestions__close-btn"
              onClick={onClose}
              aria-label="Close suggestions panel"
            >
              <X size={16} aria-hidden="true" />
            </button>
          )}
        </div>
      </div>

      {error && (
        <div className="task-ai-suggestions__error" role="alert">
          <div className="task-ai-suggestions__error-content">
            <AlertCircle size={16} aria-hidden="true" />
            <span>{error}</span>
          </div>
          <div className="task-ai-suggestions__error-actions">
            <Button variant="secondary" size="sm" onClick={handleFetchSuggestions}>
              Try again
            </Button>
            <button
              type="button"
              className="task-ai-suggestions__dismiss-btn"
              onClick={() => setError("")}
              aria-label="Dismiss error"
            >
              <X size={14} aria-hidden="true" />
            </button>
          </div>
        </div>
      )}

      {successMessage && (
        <div className="task-ai-suggestions__success" role="status">
          <CheckCircle2 size={16} className="task-ai-suggestions__success-icon" aria-hidden="true" />
          <div className="task-ai-suggestions__success-content">
            <span className="task-ai-suggestions__success-text">{successMessage}</span>
            {newlyCreatedTasks.length > 0 && (
              <ul className="task-ai-suggestions__created-list">
                {newlyCreatedTasks.map((t) => (
                  <li key={t.id} className="task-ai-suggestions__created-item">
                    <Check size={12} aria-hidden="true" />
                    <span>{t.title}</span>
                  </li>
                ))}
              </ul>
            )}
          </div>
          <button
            type="button"
            className="task-ai-suggestions__dismiss-btn"
            onClick={() => setSuccessMessage("")}
            aria-label="Dismiss success message"
          >
            <X size={14} aria-hidden="true" />
          </button>
        </div>
      )}

      {isGenerating && (
        <div className="task-ai-suggestions__loading-state" role="status" aria-live="polite">
          <Spinner size="md" label="Analyzing project" />
          <p className="task-ai-suggestions__loading-title">
            {isTaskLevel ? "Analyzing task context..." : "Analyzing project..."}
          </p>
          <p className="task-ai-suggestions__loading-subtext">
            Finding missing tasks and reviewing existing scope...
          </p>
        </div>
      )}

      {!isGenerating && suggestions === null && !successMessage && (
        <div className="task-ai-suggestions__initial-state">
          <p className="task-ai-suggestions__initial-text">
            {isTaskLevel
              ? "Discover complementary testing, error handling, validation, or follow-up tasks tailored to this task definition."
              : "Discover missing implementation tasks, automated tests, security hardening, and operational requirements tailored to your project."}
          </p>
          <Button
            variant="primary"
            onClick={handleFetchSuggestions}
            disabled={isGenerating}
            className="task-ai-suggestions__trigger-btn"
          >
            <Sparkles size={16} aria-hidden="true" />
            {isTaskLevel ? "Suggest Related Tasks" : "Suggest Tasks with AI"}
          </Button>
        </div>
      )}

      {!isGenerating && suggestions !== null && totalCount === 0 && (
        <div className="task-ai-suggestions__empty-state">
          <div className="task-ai-suggestions__empty-icon-wrap">
            <CheckCircle2 size={24} aria-hidden="true" />
          </div>
          <h3 className="task-ai-suggestions__empty-title">No additional tasks identified</h3>
          <p className="task-ai-suggestions__empty-text">
            No additional tasks were identified from the current project context.
          </p>
          <Button variant="secondary" size="sm" onClick={handleFetchSuggestions}>
            <RefreshCw size={14} aria-hidden="true" />
            Check again
          </Button>
        </div>
      )}

      {!isGenerating && suggestions !== null && totalCount > 0 && (
        <div className="task-ai-suggestions__content">
          <div className="task-ai-suggestions__toolbar">
            <span className="task-ai-suggestions__context-label">
              {isTaskLevel ? "Based on this task and project:" : "Based on your current project:"}
            </span>
            <div className="task-ai-suggestions__selection-controls">
              <span className="task-ai-suggestions__counter">
                {selectedCount} of {totalCount} selected
              </span>
              <button
                type="button"
                className="task-ai-suggestions__link-btn"
                onClick={handleSelectAll}
                disabled={selectedCount === totalCount}
              >
                Select all
              </button>
              <span className="task-ai-suggestions__separator">·</span>
              <button
                type="button"
                className="task-ai-suggestions__link-btn"
                onClick={handleDeselectAll}
                disabled={selectedCount === 0}
              >
                Deselect all
              </button>
            </div>
          </div>

          <div className="task-ai-suggestions__list" role="group" aria-label="Task suggestions">
            {suggestions.map((sug, idx) => {
              const isSelected = selectedIndices.has(idx);
              const priKey = (sug.priority || "medium").toLowerCase();
              const priMeta = TASK_PRIORITY_META[priKey] || TASK_PRIORITY_META.medium;
              const PriorityIcon = priMeta.icon;

              return (
                <div
                  key={`sug-${idx}`}
                  className={`task-ai-suggestions__item ${
                    isSelected ? "task-ai-suggestions__item--selected" : ""
                  }`}
                  onClick={() => handleToggleSelect(idx)}
                  role="checkbox"
                  aria-checked={isSelected}
                  tabIndex={0}
                  onKeyDown={(e) => {
                    if (e.key === " " || e.key === "Enter") {
                      e.preventDefault();
                      handleToggleSelect(idx);
                    }
                  }}
                >
                  <div className="task-ai-suggestions__item-checkbox">
                    <input
                      type="checkbox"
                      id={`suggestion-chk-${idx}`}
                      checked={isSelected}
                      onChange={() => handleToggleSelect(idx)}
                      onClick={(e) => e.stopPropagation()}
                      aria-label={`Select ${sug.title}`}
                    />
                  </div>

                  <div className="task-ai-suggestions__item-body">
                    <div className="task-ai-suggestions__item-header">
                      <span className="task-ai-suggestions__item-title">{sug.title}</span>
                      <Badge variant={priMeta.badgeVariant} className="task-ai-suggestions__priority-badge">
                        <PriorityIcon size={12} aria-hidden="true" />
                        {priMeta.label}
                      </Badge>
                    </div>

                    {sug.description && (
                      <p className="task-ai-suggestions__item-desc">{sug.description}</p>
                    )}

                    {sug.reason && (
                      <div className="task-ai-suggestions__item-reason">
                        <span className="task-ai-suggestions__reason-label">Why:</span>
                        <span className="task-ai-suggestions__reason-text">{sug.reason}</span>
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>

          <div className="task-ai-suggestions__actions">
            <Button
              variant="primary"
              disabled={selectedCount === 0 || isApplying}
              onClick={handleApply}
            >
              {isApplying ? (
                <>
                  <Spinner size="sm" label="Creating tasks" />
                  Creating selected tasks...
                </>
              ) : (
                <>
                  <Plus size={16} aria-hidden="true" />
                  Create Selected Tasks {selectedCount > 0 ? `(${selectedCount})` : ""}
                </>
              )}
            </Button>

            <Button
              variant="secondary"
              disabled={isApplying}
              onClick={handleCancel}
            >
              Cancel
            </Button>
          </div>
        </div>
      )}
    </Card>
  );
}

export default TaskAISuggestions;
