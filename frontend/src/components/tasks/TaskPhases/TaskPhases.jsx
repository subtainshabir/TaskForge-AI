import { useCallback, useEffect, useMemo, useState } from "react";
import {
  AlertCircle,
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

function TaskPhases({ taskId, onPhaseChange }) {
  const [phases, setPhases] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");

  const [isGenerating, setIsGenerating] = useState(false);
  const [generateError, setGenerateError] = useState("");
  const [isConfirmRegenOpen, setIsConfirmRegenOpen] = useState(false);

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
                onClick={() => setIsConfirmRegenOpen(true)}
                disabled={isGenerating}
                aria-label="Regenerate phases with AI"
              >
                <RefreshCw size={14} aria-hidden="true" />
                Regenerate phases
              </Button>
              <Button variant="secondary" size="sm" onClick={openAddModal} disabled={isGenerating}>
                <Plus size={14} aria-hidden="true" />
                Add phase
              </Button>
            </>
          ) : (
            <Button
              variant="primary"
              size="sm"
              onClick={() => handleGenerate(false)}
              disabled={isGenerating}
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
