import { useState } from "react";
import {
  Sparkles,
  RotateCw,
  X,
  AlertCircle,
  AlertTriangle,
  Check,
  ArrowRight,
  Split,
  Eye,
  FileCheck,
} from "lucide-react";
import Spinner from "../../Spinner/Spinner.jsx";
import Button from "../../Button/Button.jsx";
import Badge from "../../Badge/Badge.jsx";
import RichTextViewer from "../RichTextViewer/RichTextViewer.jsx";
import "./NoteAIImprovement.css";

const CATEGORY_LABELS = {
  clarity: "Clarity",
  grammar: "Grammar",
  structure: "Structure",
  conciseness: "Conciseness",
  organization: "Organization",
};

function NoteAIImprovement({
  originalNote,
  improvement,
  isLoading = false,
  error = "",
  isApplying = false,
  onRegenerate,
  onKeepOriginal,
  onClose,
  onApply,
}) {
  const [activeView, setActiveView] = useState("compare"); // 'compare' | 'improved-only'

  if (!isLoading && !error && !improvement) {
    return null;
  }

  const hasTitleChange =
    improvement?.improved_title &&
    originalNote?.title &&
    improvement.improved_title.trim() !== originalNote.title.trim();

  const handleApplyClick = () => {
    if (!improvement || isApplying || !onApply) return;
    onApply(
      improvement.improved_title || originalNote?.title || "",
      improvement.improved_content || originalNote?.content || ""
    );
  };

  const handleKeepClick = () => {
    if (isApplying) return;
    if (onKeepOriginal) {
      onKeepOriginal();
    } else if (onClose) {
      onClose();
    }
  };

  return (
    <section
      className="note-ai-improvement"
      role="region"
      aria-label="AI Note Improvement Review"
    >
      {/* Header */}
      <div className="note-ai-improvement__header">
        <div className="note-ai-improvement__title-group">
          <Sparkles
            size={16}
            className="note-ai-improvement__sparkle-icon"
            aria-hidden="true"
          />
          <h3 className="note-ai-improvement__title">AI Note Improvement</h3>
          <span className="note-ai-improvement__badge">AI-Generated</span>
          {improvement?.changes?.length > 0 && (
            <span className="note-ai-improvement__count-badge">
              {improvement.changes.length}{" "}
              {improvement.changes.length === 1 ? "improvement" : "improvements"}
            </span>
          )}
        </div>

        <div className="note-ai-improvement__header-actions">
          {onRegenerate && (
            <button
              type="button"
              className="note-ai-improvement__action-btn"
              onClick={onRegenerate}
              disabled={isLoading || isApplying}
              title="Regenerate AI improvements"
              aria-label="Regenerate AI improvements"
            >
              <RotateCw
                size={14}
                className={isLoading ? "note-ai-improvement__spin" : ""}
                aria-hidden="true"
              />
              <span>Regenerate</span>
            </button>
          )}
          {(onClose || onKeepOriginal) && (
            <button
              type="button"
              className="note-ai-improvement__close-btn"
              onClick={handleKeepClick}
              disabled={isApplying}
              title="Keep original and close suggestion"
              aria-label="Keep original and close suggestion"
            >
              <X size={15} aria-hidden="true" />
            </button>
          )}
        </div>
      </div>

      {/* Loading State */}
      {isLoading && (
        <div className="note-ai-improvement__loading">
          <Spinner size="md" />
          <div className="note-ai-improvement__loading-text">
            <span className="note-ai-improvement__loading-title">
              Reviewing your note...
            </span>
            <small className="note-ai-improvement__loading-desc">
              Analyzing clarity, structure, grammar, conciseness, and organization...
            </small>
          </div>
        </div>
      )}

      {/* Error State */}
      {!isLoading && error && (
        <div className="note-ai-improvement__error-banner" role="alert">
          <AlertCircle size={18} className="note-ai-improvement__error-icon" />
          <div className="note-ai-improvement__error-content">
            <span className="note-ai-improvement__error-title">
              Unable to review note
            </span>
            <span className="note-ai-improvement__error-desc">{error}</span>
          </div>
          {onRegenerate && (
            <Button
              variant="secondary"
              size="sm"
              onClick={onRegenerate}
              className="note-ai-improvement__retry-btn"
            >
              Try Again
            </Button>
          )}
        </div>
      )}

      {/* Improvement Review Content */}
      {!isLoading && !error && improvement && (
        <div className="note-ai-improvement__body">
          {/* View Mode Switcher */}
          <div className="note-ai-improvement__toolbar">
            <div className="note-ai-improvement__view-toggles">
              <button
                type="button"
                className={`note-ai-improvement__toggle-btn ${
                  activeView === "compare"
                    ? "note-ai-improvement__toggle-btn--active"
                    : ""
                }`}
                onClick={() => setActiveView("compare")}
              >
                <Split size={14} aria-hidden="true" />
                <span>Side-by-Side Comparison</span>
              </button>
              <button
                type="button"
                className={`note-ai-improvement__toggle-btn ${
                  activeView === "improved-only"
                    ? "note-ai-improvement__toggle-btn--active"
                    : ""
                }`}
                onClick={() => setActiveView("improved-only")}
              >
                <Eye size={14} aria-hidden="true" />
                <span>Improved View Only</span>
              </button>
            </div>

            {hasTitleChange && (
              <div className="note-ai-improvement__title-diff-pill">
                <span className="note-ai-improvement__title-diff-label">
                  Suggested Title:
                </span>
                <strong>{improvement.improved_title}</strong>
              </div>
            )}
          </div>

          {/* Comparison Panels */}
          <div
            className={`note-ai-improvement__panels ${
              activeView === "improved-only"
                ? "note-ai-improvement__panels--single"
                : ""
            }`}
          >
            {/* Original Note Panel */}
            {activeView === "compare" && (
              <div className="note-ai-improvement__panel note-ai-improvement__panel--original">
                <div className="note-ai-improvement__panel-header">
                  <div className="note-ai-improvement__panel-title-wrap">
                    <span className="note-ai-improvement__panel-badge note-ai-improvement__panel-badge--original">
                      Original
                    </span>
                    <h4
                      className="note-ai-improvement__panel-note-title"
                      title={originalNote?.title}
                    >
                      {originalNote?.title || "Untitled Note"}
                    </h4>
                  </div>
                </div>
                <div className="note-ai-improvement__panel-body">
                  <RichTextViewer
                    content={originalNote?.content || ""}
                    emptyMessage="Original note had no additional content."
                  />
                </div>
              </div>
            )}

            {/* AI Improved Version Panel */}
            <div className="note-ai-improvement__panel note-ai-improvement__panel--improved">
              <div className="note-ai-improvement__panel-header">
                <div className="note-ai-improvement__panel-title-wrap">
                  <span className="note-ai-improvement__panel-badge note-ai-improvement__panel-badge--improved">
                    AI Suggested
                  </span>
                  <h4
                    className="note-ai-improvement__panel-note-title note-ai-improvement__panel-note-title--highlight"
                    title={improvement.improved_title}
                  >
                    {improvement.improved_title}
                  </h4>
                </div>
              </div>
              <div className="note-ai-improvement__panel-body">
                <RichTextViewer
                  content={improvement.improved_content || ""}
                  emptyMessage="No content suggested."
                />
              </div>
            </div>
          </div>

          {/* Changes Breakdown */}
          {improvement.changes && improvement.changes.length > 0 && (
            <div className="note-ai-improvement__changes-section">
              <div className="note-ai-improvement__changes-header">
                <FileCheck
                  size={15}
                  className="note-ai-improvement__changes-icon"
                  aria-hidden="true"
                />
                <h4 className="note-ai-improvement__changes-title">
                  Detected Improvements
                </h4>
              </div>

              <div className="note-ai-improvement__changes-grid">
                {improvement.changes.map((change, idx) => {
                  const catKey = (change.category || "clarity").toLowerCase();
                  const catLabel = CATEGORY_LABELS[catKey] || change.category;
                  return (
                    <div
                      key={idx}
                      className={`note-ai-improvement__change-card note-ai-improvement__change-card--${catKey}`}
                    >
                      <span
                        className={`note-ai-improvement__category-pill note-ai-improvement__category-pill--${catKey}`}
                      >
                        {catLabel}
                      </span>
                      <p className="note-ai-improvement__change-desc">
                        {change.description}
                      </p>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Warnings (if any) */}
          {improvement.warnings && improvement.warnings.length > 0 && (
            <div className="note-ai-improvement__warnings-box" role="alert">
              <AlertTriangle
                size={16}
                className="note-ai-improvement__warning-icon"
                aria-hidden="true"
              />
              <div className="note-ai-improvement__warning-list">
                {improvement.warnings.map((warn, idx) => (
                  <p key={idx} className="note-ai-improvement__warning-text">
                    {warn}
                  </p>
                ))}
              </div>
            </div>
          )}

          {/* Action Footer */}
          <div className="note-ai-improvement__footer">
            <div className="note-ai-improvement__footer-hint">
              <span>
                Review the changes above. Your original note remains untouched
                until you choose <strong>Apply Changes</strong>.
              </span>
            </div>

            <div className="note-ai-improvement__footer-buttons">
              <Button
                type="button"
                variant="secondary"
                onClick={handleKeepClick}
                disabled={isApplying}
                className="note-ai-improvement__btn-keep"
              >
                Keep Original
              </Button>
              <Button
                type="button"
                variant="primary"
                onClick={handleApplyClick}
                disabled={isApplying}
                loading={isApplying}
                className="note-ai-improvement__btn-apply"
              >
                {!isApplying && (
                  <Check size={16} aria-hidden="true" />
                )}
                <span>{isApplying ? "Applying Changes..." : "Apply Changes"}</span>
              </Button>
            </div>
          </div>
        </div>
      )}
    </section>
  );
}

export default NoteAIImprovement;
