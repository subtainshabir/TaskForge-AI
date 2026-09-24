import { useCallback, useEffect, useMemo, useState } from "react";
import {
  AlertCircle,
  ArrowRight,
  Check,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  Circle,
  Edit2,
  Layers,
  PlayCircle,
  Plus,
  RefreshCw,
  Sparkles,
  Trash2,
  X,
} from "lucide-react";
import Card from "../../Card/Card.jsx";
import Button from "../../Button/Button.jsx";
import Badge from "../../Badge/Badge.jsx";
import Modal from "../../Modal/Modal.jsx";
import Spinner from "../../Spinner/Spinner.jsx";
import { taskService } from "../../../services/taskService.js";
import { apiErrorMessage } from "../../../utils/apiErrorMessage.js";
import "./TaskPhases.css";

const PHASE_STATUS_META = {
  todo: { label: "To Do", badgeVariant: "neutral", icon: Circle },
  in_progress: { label: "In Progress", badgeVariant: "accent", icon: PlayCircle },
  completed: { label: "Completed", badgeVariant: "success", icon: CheckCircle2 },
};

function getSuggestionBadgeVariant(type) {
  switch (type) {
    case "add":
      return "success";
    case "remove":
      return "danger";
    case "split":
      return "ai";
    case "rename":
      return "accent";
    default:
      return "neutral";
  }
}

function formatSuggestionType(type) {
  switch (type) {
    case "add":
      return "Add";
    case "rename":
      return "Rename";
    case "split":
      return "Split";
    case "remove":
      return "Remove";
    case "reorder":
      return "Reorder";
    case "update_description":
      return "Update Scope";
    default:
      return type;
  }
}

function TaskPhases({ taskId, onPhaseChange }) {
  const [phases, setPhases] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");

  const [isGenerating, setIsGenerating] = useState(false);
  const [generateError, setGenerateError] = useState("");
  const [isConfirmRegenOpen, setIsConfirmRegenOpen] = useState(false);

  const [isReviewing, setIsReviewing] = useState(false);
  const [refineError, setRefineError] = useState("");
  const [refinementResult, setRefinementResult] = useState(null);
  const [selectedSuggestionIds, setSelectedSuggestionIds] = useState(new Set());
  const [isApplyingRefinements, setIsApplyingRefinements] = useState(false);
  const [applyError, setApplyError] = useState("");

  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingPhase, setEditingPhase] = useState(null);
  const [modalTitle, setModalTitle] = useState("");
  const [modalDescription, setModalDescription] = useState("");
  const [modalStatus, setModalStatus] = useState("todo");
  const [modalError, setModalError] = useState("");
  const [isSaving, setIsSaving] = useState(false);

  const [deletingId, setDeletingId] = useState(null);

  const loadPhases = useCallback(async () => {
    setIsLoading(true);
    setError("");
    try {
      const data = await taskService.getPhases(taskId);
      setPhases(Array.isArray(data) ? data : []);
    } catch (err) {
      setError(apiErrorMessage(err, "Failed to load task phases."));
    } finally {
      setIsLoading(false);
    }
  }, [taskId]);

  useEffect(() => {
    loadPhases();
  }, [loadPhases]);

  const totalPhases = phases.length;
  const completedPhases = useMemo(
    () => phases.filter((p) => p.status === "completed").length,
    [phases]
  );
  const progressPercent = useMemo(
    () => (totalPhases === 0 ? 0 : Math.round((completedPhases / totalPhases) * 100)),
    [totalPhases, completedPhases]
  );

  const handleGenerate = async (replaceExisting = false) => {
    if (isGenerating) return;
    setIsGenerating(true);
    setGenerateError("");
    setIsConfirmRegenOpen(false);

    try {
      const newPhases = await taskService.generatePhases(taskId, replaceExisting);
      setPhases(Array.isArray(newPhases) ? newPhases : []);
      onPhaseChange?.();
    } catch (err) {
      setGenerateError(
        apiErrorMessage(
          err,
          "Failed to generate phases with AI. Please check your AI configuration and try again."
        )
      );
    } finally {
      setIsGenerating(false);
    }
  };

  const handleReviewPhases = async () => {
    if (isReviewing || isGenerating) return;
    setIsReviewing(true);
    setRefineError("");
    setApplyError("");

    try {
      const data = await taskService.refinePhases(taskId);
      setRefinementResult(data);
      const suggestions = Array.isArray(data?.suggestions) ? data.suggestions : [];
      const allIds = new Set(suggestions.map((s, idx) => s.id || `sug-${idx}`));
      setSelectedSuggestionIds(allIds);
    } catch (err) {
      setRefineError(
        apiErrorMessage(
          err,
          "Failed to review phases with AI. Please check your AI configuration and try again."
        )
      );
    } finally {
      setIsReviewing(false);
    }
  };

  const handleToggleSelectSuggestion = (sugId) => {
    setSelectedSuggestionIds((prev) => {
      const next = new Set(prev);
      if (next.has(sugId)) {
        next.delete(sugId);
      } else {
        next.add(sugId);
      }
      return next;
    });
  };

  const handleSelectAllSuggestions = () => {
    if (!refinementResult?.suggestions) return;
    const allIds = new Set(refinementResult.suggestions.map((s, idx) => s.id || `sug-${idx}`));
    setSelectedSuggestionIds(allIds);
  };

  const handleDeselectAllSuggestions = () => {
    setSelectedSuggestionIds(new Set());
  };

  const handleCancelReview = () => {
    setRefinementResult(null);
    setSelectedSuggestionIds(new Set());
    setRefineError("");
    setApplyError("");
  };

  const handleApplyRefinements = async () => {
    if (!refinementResult?.suggestions || isApplyingRefinements) return;

    const selectedSuggestions = refinementResult.suggestions.filter((s, idx) => {
      const sugId = s.id || `sug-${idx}`;
      return selectedSuggestionIds.has(sugId);
    });

    if (selectedSuggestions.length === 0) return;

    setIsApplyingRefinements(true);
    setApplyError("");

    try {
      const updatedPhases = await taskService.applyPhaseRefinements(taskId, selectedSuggestions);
      setPhases(Array.isArray(updatedPhases) ? updatedPhases : []);
      setRefinementResult(null);
      setSelectedSuggestionIds(new Set());
      onPhaseChange?.();
    } catch (err) {
      setApplyError(
        apiErrorMessage(
          err,
          "Failed to apply phase suggestions. Please verify the phase list and try again."
        )
      );
    } finally {
      setIsApplyingRefinements(false);
    }
  };

  const handleToggleComplete = async (phase) => {
    const nextStatus = phase.status === "completed" ? "todo" : "completed";
    try {
      const updated = await taskService.updatePhase(taskId, phase.id, {
        status: nextStatus,
      });
      setPhases((prev) => prev.map((p) => (p.id === phase.id ? updated : p)));
      onPhaseChange?.();
    } catch (err) {
      setError(apiErrorMessage(err, "Failed to update phase status."));
    }
  };

  const handleStatusChange = async (phase, nextStatus) => {
    if (phase.status === nextStatus) return;
    try {
      const updated = await taskService.updatePhase(taskId, phase.id, {
        status: nextStatus,
      });
      setPhases((prev) => prev.map((p) => (p.id === phase.id ? updated : p)));
      onPhaseChange?.();
    } catch (err) {
      setError(apiErrorMessage(err, "Failed to update phase status."));
    }
  };

  const handleDelete = async (phaseId) => {
    setDeletingId(phaseId);
    try {
      await taskService.deletePhase(taskId, phaseId);
      setPhases((prev) => prev.filter((p) => p.id !== phaseId));
      onPhaseChange?.();
    } catch (err) {
      setError(apiErrorMessage(err, "Failed to delete phase."));
    } finally {
      setDeletingId(null);
    }
  };

  const openAddModal = () => {
    setEditingPhase(null);
    setModalTitle("");
    setModalDescription("");
    setModalStatus("todo");
    setModalError("");
    setIsModalOpen(true);
  };

  const openEditModal = (phase) => {
    setEditingPhase(phase);
    setModalTitle(phase.title);
    setModalDescription(phase.description || "");
    setModalStatus(phase.status || "todo");
    setModalError("");
    setIsModalOpen(true);
  };

  const handleSaveModal = async (e) => {
    e.preventDefault();
    if (!modalTitle.trim()) {
      setModalError("Phase title cannot be empty");
      return;
    }

    setIsSaving(true);
    setModalError("");

    try {
      if (editingPhase) {
        const updated = await taskService.updatePhase(taskId, editingPhase.id, {
          title: modalTitle.trim(),
          description: modalDescription.trim() || null,
          status: modalStatus,
        });
        setPhases((prev) => prev.map((p) => (p.id === editingPhase.id ? updated : p)));
      } else {
        const created = await taskService.createPhase(taskId, {
          title: modalTitle.trim(),
          description: modalDescription.trim() || null,
          status: modalStatus,
          order_index: phases.length,
        });
        setPhases((prev) => [...prev, created]);
      }
      setIsModalOpen(false);
      onPhaseChange?.();
    } catch (err) {
      setModalError(apiErrorMessage(err, "Failed to save phase."));
    } finally {
      setIsSaving(false);
    }
  };

  const handleMoveOrder = async (index, direction) => {
    const targetIndex = direction === "up" ? index - 1 : index + 1;
    if (targetIndex < 0 || targetIndex >= phases.length) return;

    const sourcePhase = phases[index];
    const targetPhase = phases[targetIndex];

    const sourceOrder = sourcePhase.order_index ?? index;
    const targetOrder = targetPhase.order_index ?? targetIndex;

    const newPhases = [...phases];
    newPhases[index] = { ...targetPhase, order_index: sourceOrder };
    newPhases[targetIndex] = { ...sourcePhase, order_index: targetOrder };
    setPhases(newPhases);

    try {
      await Promise.all([
        taskService.updatePhase(taskId, sourcePhase.id, { order_index: targetOrder }),
        taskService.updatePhase(taskId, targetPhase.id, { order_index: sourceOrder }),
      ]);
    } catch (err) {
      loadPhases();
    }
  };

  return (
    <Card className={`task-phases ${totalPhases > 0 ? "task-phases--has-items" : ""}`}>
      <div className="task-phases__header">
        <div className="task-phases__title-group">
          <h2 className="task-phases__title">
            <Layers size={20} className="task-phases__icon" aria-hidden="true" />
            Phases
          </h2>
          {totalPhases > 0 && (
            <span className="task-phases__count-pill">
              {completedPhases} / {totalPhases} completed
            </span>
          )}
        </div>

        <div className="task-phases__actions">
          {totalPhases > 0 ? (
            <>
              <Button
                variant="secondary"
                size="sm"
                onClick={handleReviewPhases}
                disabled={isReviewing || isGenerating}
                aria-label="Review phases with AI"
              >
                {isReviewing ? (
                  <>
                    <Spinner size="sm" label="Reviewing" />
                    Reviewing phases...
                  </>
                ) : (
                  <>
                    <Sparkles size={14} aria-hidden="true" />
                    Review phases with AI
                  </>
                )}
              </Button>
              <Button
                variant="secondary"
                size="sm"
                onClick={() => setIsConfirmRegenOpen(true)}
                disabled={isGenerating || isReviewing}
                aria-label="Regenerate phases with AI"
              >
                <RefreshCw size={14} aria-hidden="true" />
                Regenerate phases
              </Button>
              <Button
                variant="secondary"
                size="sm"
                onClick={openAddModal}
                disabled={isGenerating || isReviewing}
              >
                <Plus size={14} aria-hidden="true" />
                Add phase
              </Button>
            </>
          ) : (
            <Button
              variant="primary"
              size="sm"
              onClick={() => handleGenerate(false)}
              disabled={isGenerating || isReviewing}
              aria-label="Generate phases with AI"
            >
              {isGenerating ? (
                <>
                  <Spinner size="sm" label="Generating" />
                  Generating phases...
                </>
              ) : (
                <>
                  <Sparkles size={14} aria-hidden="true" />
                  Generate phases with AI
                </>
              )}
            </Button>
          )}
        </div>
      </div>

      {totalPhases > 0 && (
        <div className="task-phases__progress-section">
          <div className="task-phases__progress-labels">
            <span className="task-phases__progress-title">Progress</span>
            <span className="task-phases__progress-value">{progressPercent}%</span>
          </div>
          <div
            className="task-phases__progress-bar-track"
            role="progressbar"
            aria-valuenow={progressPercent}
            aria-valuemin="0"
            aria-valuemax="100"
          >
            <div
              className="task-phases__progress-bar-fill"
              style={{ width: `${progressPercent}%` }}
            />
          </div>
        </div>
      )}

      {error && (
        <div className="task-phases__error" role="alert">
          <AlertCircle size={16} aria-hidden="true" />
          <span>{error}</span>
          <Button variant="secondary" size="sm" onClick={loadPhases}>
            Retry
          </Button>
        </div>
      )}

      {generateError && (
        <div className="task-phases__error" role="alert">
          <AlertCircle size={16} aria-hidden="true" />
          <span>{generateError}</span>
          <Button variant="secondary" size="sm" onClick={() => handleGenerate(totalPhases > 0)}>
            Try again
          </Button>
        </div>
      )}

      {refineError && (
        <div className="task-phases__error" role="alert">
          <AlertCircle size={16} aria-hidden="true" />
          <span>{refineError}</span>
          <Button variant="secondary" size="sm" onClick={handleReviewPhases}>
            Try again
          </Button>
        </div>
      )}

      {isReviewing && (
        <div className="task-phases__loading-state" aria-live="polite">
          <Spinner size="lg" label="Reviewing phases" />
          <p className="task-phases__loading-text">
            Reviewing current phases and analyzing potential improvements...
          </p>
        </div>
      )}

      {refinementResult && (
        <div className="task-phases__refinement-panel" role="region" aria-label="AI Phase Review">
          <div className="task-phases__refinement-header">
            <div className="task-phases__refinement-title-group">
              <Sparkles size={18} className="task-phases__refinement-sparkle" aria-hidden="true" />
              <h3 className="task-phases__refinement-heading">AI Phase Review</h3>
              <span className="task-phases__refinement-count-pill">
                {refinementResult.suggestions.length} suggestion
                {refinementResult.suggestions.length === 1 ? "" : "s"} found
              </span>
            </div>
            <button
              type="button"
              className="task-phases__icon-btn"
              onClick={handleCancelReview}
              aria-label="Close review"
              title="Close review"
            >
              <X size={16} />
            </button>
          </div>

          {refinementResult.summary && (
            <div className="task-phases__refinement-summary">
              <p className="task-phases__refinement-summary-text">{refinementResult.summary}</p>
            </div>
          )}

          {applyError && (
            <div className="task-phases__error" role="alert">
              <AlertCircle size={16} aria-hidden="true" />
              <span>{applyError}</span>
            </div>
          )}

          <div className="task-phases__refinement-toolbar">
            <span className="task-phases__refinement-selected-count">
              {selectedSuggestionIds.size} of {refinementResult.suggestions.length} selected
            </span>
            <div className="task-phases__refinement-toolbar-actions">
              <button
                type="button"
                className="task-phases__refinement-link-btn"
                onClick={handleSelectAllSuggestions}
                disabled={selectedSuggestionIds.size === refinementResult.suggestions.length}
              >
                Select all
              </button>
              <span className="task-phases__refinement-divider">•</span>
              <button
                type="button"
                className="task-phases__refinement-link-btn"
                onClick={handleDeselectAllSuggestions}
                disabled={selectedSuggestionIds.size === 0}
              >
                Deselect all
              </button>
            </div>
          </div>

          <div className="task-phases__refinement-list">
            {refinementResult.suggestions.map((sug, idx) => {
              const sugId = sug.id || `sug-${idx}`;
              const isChecked = selectedSuggestionIds.has(sugId);
              return (
                <div
                  key={sugId}
                  className={`task-phases__suggestion-item ${
                    isChecked ? "task-phases__suggestion-item--selected" : ""
                  }`}
                  onClick={() => handleToggleSelectSuggestion(sugId)}
                >
                  <div className="task-phases__suggestion-checkbox-wrap">
                    <input
                      type="checkbox"
                      id={`suggestion-${sugId}`}
                      checked={isChecked}
                      onChange={() => handleToggleSelectSuggestion(sugId)}
                      onClick={(e) => e.stopPropagation()}
                      className="task-phases__suggestion-checkbox"
                      aria-label={`Select suggestion ${sug.type} ${sug.proposed_title || sug.title}`}
                    />
                  </div>
                  <div className="task-phases__suggestion-content">
                    <div className="task-phases__suggestion-header-row">
                      <Badge variant={getSuggestionBadgeVariant(sug.type)}>
                        {formatSuggestionType(sug.type)}
                      </Badge>
                      {sug.type === "rename" && (
                        <span className="task-phases__suggestion-title-line">
                          Rename <strong>"{sug.title}"</strong>
                        </span>
                      )}
                      {sug.type === "split" && (
                        <span className="task-phases__suggestion-title-line">
                          Split <strong>"{sug.title}"</strong>
                        </span>
                      )}
                      {sug.type === "remove" && (
                        <span className="task-phases__suggestion-title-line">
                          Remove <strong>"{sug.title}"</strong>
                        </span>
                      )}
                      {sug.type === "add" && (
                        <span className="task-phases__suggestion-title-line">
                          Add <strong>"{sug.proposed_title || sug.title}"</strong>
                        </span>
                      )}
                      {sug.type === "reorder" && (
                        <span className="task-phases__suggestion-title-line">
                          Reorder <strong>"{sug.title}"</strong>
                        </span>
                      )}
                      {sug.type === "update_description" && (
                        <span className="task-phases__suggestion-title-line">
                          Update scope for <strong>"{sug.title}"</strong>
                        </span>
                      )}
                    </div>

                    {sug.type === "rename" && (
                      <div className="task-phases__suggestion-detail">
                        <ArrowRight size={14} className="task-phases__suggestion-arrow" aria-hidden="true" />
                        <span className="task-phases__suggestion-target-title">
                          "{sug.proposed_title}"
                        </span>
                      </div>
                    )}

                    {sug.type === "split" && sug.split_phases && (
                      <div className="task-phases__suggestion-split-list">
                        {sug.split_phases.map((sp, spIdx) => (
                          <div key={spIdx} className="task-phases__suggestion-split-item">
                            <ArrowRight size={13} className="task-phases__suggestion-arrow" aria-hidden="true" />
                            <span className="task-phases__suggestion-split-title">{sp.title}</span>
                            {sp.description && (
                              <span className="task-phases__suggestion-split-desc">
                                — {sp.description}
                              </span>
                            )}
                          </div>
                        ))}
                      </div>
                    )}

                    {sug.type === "add" && sug.proposed_description && (
                      <p className="task-phases__suggestion-desc">{sug.proposed_description}</p>
                    )}

                    {sug.type === "reorder" && (
                      <div className="task-phases__suggestion-detail">
                        <ArrowRight size={14} className="task-phases__suggestion-arrow" aria-hidden="true" />
                        <span>Move to position {(sug.proposed_order ?? 0) + 1}</span>
                      </div>
                    )}

                    {sug.type === "update_description" && sug.proposed_description && (
                      <p className="task-phases__suggestion-desc">Scope: {sug.proposed_description}</p>
                    )}

                    {sug.description && (
                      <p className="task-phases__suggestion-rationale">{sug.description}</p>
                    )}
                  </div>
                </div>
              );
            })}
          </div>

          <div className="task-phases__refinement-actions">
            <Button
              variant="primary"
              onClick={handleApplyRefinements}
              disabled={isApplyingRefinements || selectedSuggestionIds.size === 0}
            >
              {isApplyingRefinements ? (
                <>
                  <Spinner size="sm" label="Applying changes" />
                  Applying selected changes...
                </>
              ) : (
                `Apply Selected (${selectedSuggestionIds.size})`
              )}
            </Button>
            <Button
              variant="secondary"
              onClick={handleCancelReview}
              disabled={isApplyingRefinements}
            >
              Cancel
            </Button>
          </div>
        </div>
      )}

      {isLoading && (
        <div className="task-phases__loading-state" aria-live="polite">
          <Spinner size="lg" label="Loading phases" />
          <p className="task-phases__loading-text">Loading task phases...</p>
        </div>
      )}

      {isGenerating && (
        <div className="task-phases__loading-state" aria-live="polite">
          <Spinner size="lg" label="Generating phases" />
          <p className="task-phases__loading-text">
            Analyzing task requirements and generating implementation phases...
          </p>
        </div>
      )}

      {!isLoading && !isGenerating && totalPhases === 0 && (
        <div className="task-phases__empty-state">
          <div className="task-phases__empty-icon-wrap">
            <Layers size={28} className="task-phases__empty-icon" aria-hidden="true" />
          </div>
          <h3 className="task-phases__empty-heading">No phases yet</h3>
          <p className="task-phases__empty-text">
            Break this task down into sequential, independently completable implementation phases using
            AI, or create them manually.
          </p>
          <div className="task-phases__empty-buttons">
            <Button variant="primary" onClick={() => handleGenerate(false)}>
              <Sparkles size={16} aria-hidden="true" />
              Generate phases with AI
            </Button>
            <Button variant="secondary" onClick={openAddModal}>
              <Plus size={16} aria-hidden="true" />
              Add phase manually
            </Button>
          </div>
        </div>
      )}

      {!isLoading && !isGenerating && totalPhases > 0 && (
        <div className="task-phases__list">
          {phases.map((phase, index) => {
            const isCompleted = phase.status === "completed";
            const statusMeta = PHASE_STATUS_META[phase.status] || PHASE_STATUS_META.todo;
            const StatusIcon = statusMeta.icon;

            return (
              <div
                key={phase.id}
                className={`task-phases__item ${
                  isCompleted ? "task-phases__item--completed" : ""
                }`}
              >
                <div className="task-phases__item-left">
                  <button
                    type="button"
                    className={`task-phases__check-btn ${
                      isCompleted ? "task-phases__check-btn--checked" : ""
                    }`}
                    onClick={() => handleToggleComplete(phase)}
                    aria-label={
                      isCompleted ? `Mark "${phase.title}" as incomplete` : `Mark "${phase.title}" as completed`
                    }
                  >
                    {isCompleted ? (
                      <Check size={14} className="task-phases__check-icon" aria-hidden="true" />
                    ) : (
                      <Circle size={14} className="task-phases__uncheck-icon" aria-hidden="true" />
                    )}
                  </button>

                  <span className="task-phases__item-index">{index + 1}.</span>

                  <div className="task-phases__item-body">
                    <span
                      className={`task-phases__item-title ${
                        isCompleted ? "task-phases__item-title--completed" : ""
                      }`}
                    >
                      {phase.title}
                    </span>
                    {phase.description && (
                      <p className="task-phases__item-desc">{phase.description}</p>
                    )}
                  </div>
                </div>

                <div className="task-phases__item-right">
                  <div className="task-phases__status-select-wrap">
                    <select
                      className="task-phases__status-select"
                      value={phase.status}
                      onChange={(e) => handleStatusChange(phase, e.target.value)}
                      aria-label={`Status for ${phase.title}`}
                    >
                      <option value="todo">To Do</option>
                      <option value="in_progress">In Progress</option>
                      <option value="completed">Completed</option>
                    </select>
                  </div>

                  <div className="task-phases__order-buttons">
                    <button
                      type="button"
                      className="task-phases__icon-btn"
                      onClick={() => handleMoveOrder(index, "up")}
                      disabled={index === 0}
                      aria-label="Move phase up"
                      title="Move up"
                    >
                      <ChevronUp size={16} />
                    </button>
                    <button
                      type="button"
                      className="task-phases__icon-btn"
                      onClick={() => handleMoveOrder(index, "down")}
                      disabled={index === phases.length - 1}
                      aria-label="Move phase down"
                      title="Move down"
                    >
                      <ChevronDown size={16} />
                    </button>
                  </div>

                  <button
                    type="button"
                    className="task-phases__icon-btn"
                    onClick={() => openEditModal(phase)}
                    aria-label={`Edit ${phase.title}`}
                    title="Edit phase"
                  >
                    <Edit2 size={15} />
                  </button>

                  <button
                    type="button"
                    className="task-phases__icon-btn task-phases__icon-btn--danger"
                    onClick={() => handleDelete(phase.id)}
                    disabled={deletingId === phase.id}
                    aria-label={`Delete ${phase.title}`}
                    title="Delete phase"
                  >
                    <Trash2 size={15} />
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Confirmation Modal for Regeneration */}
      <Modal
        open={isConfirmRegenOpen}
        onClose={() => setIsConfirmRegenOpen(false)}
        title="Regenerate phases with AI"
      >
        <div className="task-phases__confirm-content">
          <p>
            Are you sure you want to regenerate phases with AI? This will replace your current{" "}
            <strong>{totalPhases}</strong> phase{totalPhases === 1 ? "" : "s"} with freshly generated
            phases.
          </p>
          <div className="task-phases__modal-actions">
            <Button variant="secondary" onClick={() => setIsConfirmRegenOpen(false)}>
              Cancel
            </Button>
            <Button
              variant="primary"
              onClick={() => handleGenerate(true)}
              disabled={isGenerating}
            >
              <Sparkles size={14} aria-hidden="true" />
              Regenerate phases
            </Button>
          </div>
        </div>
      </Modal>

      {/* Add / Edit Phase Modal */}
      <Modal
        open={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        title={editingPhase ? "Edit Phase" : "Add Phase"}
      >
        <form onSubmit={handleSaveModal} className="task-phases__form">
          {modalError && (
            <div className="task-phases__form-error" role="alert">
              {modalError}
            </div>
          )}

          <div className="task-phases__form-field">
            <label htmlFor="phase-title" className="task-phases__form-label">
              Title <span className="task-phases__form-required">*</span>
            </label>
            <input
              id="phase-title"
              type="text"
              className="task-phases__form-input"
              value={modalTitle}
              onChange={(e) => setModalTitle(e.target.value)}
              placeholder="e.g. Database Design"
              maxLength={255}
              autoFocus
            />
          </div>

          <div className="task-phases__form-field">
            <label htmlFor="phase-description" className="task-phases__form-label">
              Description
            </label>
            <textarea
              id="phase-description"
              className="task-phases__form-textarea"
              value={modalDescription}
              onChange={(e) => setModalDescription(e.target.value)}
              placeholder="Brief description of the work in this phase..."
              rows={3}
              maxLength={2000}
            />
          </div>

          <div className="task-phases__form-field">
            <label htmlFor="phase-status" className="task-phases__form-label">
              Status
            </label>
            <select
              id="phase-status"
              className="task-phases__form-select"
              value={modalStatus}
              onChange={(e) => setModalStatus(e.target.value)}
            >
              <option value="todo">To Do</option>
              <option value="in_progress">In Progress</option>
              <option value="completed">Completed</option>
            </select>
          </div>

          <div className="task-phases__modal-actions">
            <Button variant="secondary" type="button" onClick={() => setIsModalOpen(false)}>
              Cancel
            </Button>
            <Button variant="primary" type="submit" disabled={isSaving}>
              {isSaving ? "Saving..." : editingPhase ? "Save changes" : "Add phase"}
            </Button>
          </div>
        </form>
      </Modal>
    </Card>
  );
}

export default TaskPhases;
