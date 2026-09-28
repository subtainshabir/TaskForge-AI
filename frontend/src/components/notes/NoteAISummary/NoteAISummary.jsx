import {
  Sparkles,
  RotateCw,
  X,
  AlertCircle,
  CheckSquare,
  List,
  Info,
} from "lucide-react";
import Spinner from "../../Spinner/Spinner.jsx";
import Button from "../../Button/Button.jsx";
import "./NoteAISummary.css";

function NoteAISummary({
  summary,
  isLoading = false,
  error = "",
  onRegenerate,
  onClose,
}) {
  if (!isLoading && !error && !summary) {
    return null;
  }

  return (
    <div className="note-ai-summary" role="region" aria-label="AI Note Summary">
      <div className="note-ai-summary__header">
        <div className="note-ai-summary__title-group">
          <Sparkles size={16} className="note-ai-summary__sparkle-icon" aria-hidden="true" />
          <h3 className="note-ai-summary__title">AI Note Summary</h3>
          <span className="note-ai-summary__badge">AI-Generated</span>
        </div>

        <div className="note-ai-summary__header-actions">
          {onRegenerate && (
            <button
              type="button"
              className="note-ai-summary__action-btn"
              onClick={onRegenerate}
              disabled={isLoading}
              title="Regenerate AI summary"
              aria-label="Regenerate summary"
            >
              <RotateCw size={14} className={isLoading ? "note-ai-summary__spin" : ""} aria-hidden="true" />
              <span>Regenerate</span>
            </button>
          )}
          {onClose && (
            <button
              type="button"
              className="note-ai-summary__close-btn"
              onClick={onClose}
              title="Dismiss summary"
              aria-label="Dismiss summary"
            >
              <X size={15} aria-hidden="true" />
            </button>
          )}
        </div>
      </div>

      {isLoading && (
        <div className="note-ai-summary__loading">
          <Spinner size="sm" label="Analyzing note content..." />
          <p className="note-ai-summary__loading-text">
            Analyzing note content and extracting structured takeaways...
          </p>
        </div>
      )}

      {error && !isLoading && (
        <div className="note-ai-summary__error" role="alert">
          <AlertCircle size={16} className="note-ai-summary__error-icon" aria-hidden="true" />
          <div className="note-ai-summary__error-body">
            <span className="note-ai-summary__error-msg">{error}</span>
            {onRegenerate && (
              <button
                type="button"
                className="note-ai-summary__retry-btn"
                onClick={onRegenerate}
              >
                Try again
              </button>
            )}
          </div>
        </div>
      )}

      {summary && !isLoading && (
        <div className="note-ai-summary__body">
          {/* Executive Synthesis */}
          <div className="note-ai-summary__overview">
            <p className="note-ai-summary__overview-text">{summary.summary}</p>
          </div>

          <div className="note-ai-summary__grid">
            {/* Key Points */}
            {summary.key_points && summary.key_points.length > 0 && (
              <div className="note-ai-summary__section">
                <div className="note-ai-summary__section-header">
                  <List size={14} className="note-ai-summary__section-icon" aria-hidden="true" />
                  <h4>Key Points</h4>
                </div>
                <ul className="note-ai-summary__list">
                  {summary.key_points.map((point, idx) => (
                    <li key={idx} className="note-ai-summary__list-item">
                      {point}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Action Items */}
            {summary.action_items && summary.action_items.length > 0 && (
              <div className="note-ai-summary__section">
                <div className="note-ai-summary__section-header">
                  <CheckSquare size={14} className="note-ai-summary__section-icon" aria-hidden="true" />
                  <h4>Action Items</h4>
                </div>
                <ul className="note-ai-summary__list note-ai-summary__list--actions">
                  {summary.action_items.map((item, idx) => (
                    <li key={idx} className="note-ai-summary__list-item note-ai-summary__list-item--action">
                      <span className="note-ai-summary__checkbox-box" aria-hidden="true">☐</span>
                      <span>{item}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Important Details */}
            {summary.important_details && summary.important_details.length > 0 && (
              <div className="note-ai-summary__section">
                <div className="note-ai-summary__section-header">
                  <Info size={14} className="note-ai-summary__section-icon" aria-hidden="true" />
                  <h4>Important Details</h4>
                </div>
                <ul className="note-ai-summary__list">
                  {summary.important_details.map((detail, idx) => (
                    <li key={idx} className="note-ai-summary__list-item">
                      {detail}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

export default NoteAISummary;
