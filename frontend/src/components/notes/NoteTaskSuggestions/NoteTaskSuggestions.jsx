import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  Sparkles,
  RotateCw,
  X,
  AlertCircle,
  AlertTriangle,
  CheckCircle2,
  Calendar,
  FolderKanban,
  Flag,
  ListTodo,
  ExternalLink,
  ChevronDown,
  ChevronUp,
} from "lucide-react";
import Spinner from "../../Spinner/Spinner.jsx";
import Button from "../../Button/Button.jsx";
import Modal from "../../Modal/Modal.jsx";
import Badge from "../../Badge/Badge.jsx";
import { projectService } from "../../../services/projectService.js";
import { taskService } from "../../../services/taskService.js";
import { apiErrorMessage } from "../../../utils/apiErrorMessage.js";
import "./NoteTaskSuggestions.css";

const PRIORITY_OPTIONS = [
  { value: "low", label: "Low" },
  { value: "medium", label: "Medium" },
  { value: "high", label: "High" },
  { value: "urgent", label: "Urgent" },
];

function NoteTaskSuggestions({
  suggestionsData,
  isLoading = false,
  error = "",
  onRegenerate,
  onClose,
  currentNote = null,
  onTasksCreated,
}) {
  const [items, setItems] = useState([]);
  const [projects, setProjects] = useState([]);
  const [isLoadingProjects, setIsLoadingProjects] = useState(false);
  const [batchProjectId, setBatchProjectId] = useState("");
  const [isConfirmOpen, setIsConfirmOpen] = useState(false);
  const [isCreating, setIsCreating] = useState(false);
  const [creationResult, setCreationResult] = useState(null);
  const [validationError, setValidationError] = useState("");
  const [expandedDetails, setExpandedDetails] = useState({});

  // Fetch user projects for project selection
  useEffect(() => {
    let isMounted = true;
    async function fetchProjects() {
      setIsLoadingProjects(true);
      try {
        const projs = await projectService.list();
        if (isMounted) {
          setProjects(projs || []);
        }
      } catch {
        // Fallback gracefully
      } finally {
        if (isMounted) setIsLoadingProjects(false);
      }
    }
    fetchProjects();
    return () => {
      isMounted = false;
    };
  }, []);

  // Initialize suggestion items when suggestionsData changes
  useEffect(() => {
    if (!suggestionsData?.suggestions) {
      setItems([]);
      return;
    }

    // Determine initial project default:
    // If note belongs to a project (and NOT directly to a task), use note's project
    const defaultProjId =
      suggestionsData.project_id ||
      (currentNote?.project_id && !currentNote?.task_id
        ? currentNote.project_id
        : "");

    setBatchProjectId(defaultProjId ? String(defaultProjId) : "");

    const mapped = suggestionsData.suggestions.map((sug, idx) => ({
      id: `sug-${idx}`,
      title: sug.title || "",
      description: sug.description || "",
      priority: sug.priority || "medium",
      due_date: sug.due_date || "",
      reason: sug.reason || "",
      confidence: sug.confidence !== undefined ? sug.confidence : 0.9,
      is_duplicate: Boolean(sug.is_duplicate),
      duplicate_task_title: sug.duplicate_task_title || "",
      duplicate_dismissed: false,
      selected: !sug.is_duplicate, // Duplicates are deselected by default
      projectId: defaultProjId ? String(defaultProjId) : "",
      status: "pending", // 'pending' | 'created' | 'error'
      createdTaskId: null,
      errorMessage: "",
    }));

    setItems(mapped);
    setCreationResult(null);
    setValidationError("");
  }, [suggestionsData, currentNote]);

  if (!isLoading && !error && !suggestionsData) {
    return null;
  }

  const handleToggleSelect = (id) => {
    setItems((prev) =>
      prev.map((item) =>
        item.id === id ? { ...item, selected: !item.selected } : item
      )
    );
  };

  const handleSelectAll = (selectAll) => {
    setItems((prev) =>
      prev.map((item) =>
        item.status === "created"
          ? item
          : { ...item, selected: selectAll }
      )
    );
  };

  const handleUpdateItem = (id, field, value) => {
    setItems((prev) =>
      prev.map((item) =>
        item.id === id ? { ...item, [field]: value } : item
      )
    );
  };

  const handleBatchProjectChange = (projId) => {
    setBatchProjectId(projId);
    setItems((prev) =>
      prev.map((item) =>
        item.status === "created" ? item : { ...item, projectId: projId }
      )
    );
  };

  const handleDismissDuplicate = (id) => {
    setItems((prev) =>
      prev.map((item) =>
        item.id === id
          ? { ...item, duplicate_dismissed: true, selected: true }
          : item
      )
    );
  };

  const handleSkipDuplicate = (id) => {
    setItems((prev) =>
      prev.map((item) =>
        item.id === id ? { ...item, selected: false } : item
      )
    );
  };

  const toggleExpand = (id) => {
    setExpandedDetails((prev) => ({
      ...prev,
      [id]: !prev[id],
    }));
  };

  const selectedItems = items.filter(
    (item) => item.selected && item.status !== "created"
  );
  const selectedCount = selectedItems.length;
  const createdCount = items.filter((item) => item.status === "created").length;

  // Validate before showing confirmation modal
  const handleInitiateCreation = () => {
    setValidationError("");
    if (selectedCount === 0) {
      setValidationError("Please select at least one task to create.");
      return;
    }

    // Check titles
    const emptyTitleItem = selectedItems.find((item) => !item.title.trim());
    if (emptyTitleItem) {
      setValidationError("All selected tasks must have a valid title.");
      return;
    }

    // Check projects
    const missingProjItem = selectedItems.find(
      (item) => !item.projectId || item.projectId === ""
    );
    if (missingProjItem) {
      setValidationError(
        "Please select a target project for all selected tasks before creating."
      );
      return;
    }

    setIsConfirmOpen(true);
  };

  // Perform task creation sequentially
  const handleConfirmCreate = async () => {
    setIsCreating(true);
    setValidationError("");

    let successCount = 0;
    let failCount = 0;
    const targetProjectIds = new Set();

    const updatedItems = [...items];

    for (let i = 0; i < updatedItems.length; i++) {
      const item = updatedItems[i];
      if (!item.selected || item.status === "created") {
        continue;
      }

      try {
        const payload = {
          title: item.title.trim(),
          description: item.description.trim() || undefined,
          priority: item.priority,
          status: "todo",
        };

        if (item.due_date) {
          payload.deadline = `${item.due_date}T00:00:00Z`;
        }

        const created = await taskService.create(item.projectId, payload);
        targetProjectIds.add(item.projectId);

        updatedItems[i] = {
          ...item,
          status: "created",
          selected: false,
          createdTaskId: created.id,
          errorMessage: "",
        };
        successCount++;
      } catch (err) {
        failCount++;
        updatedItems[i] = {
          ...item,
          status: "error",
          errorMessage: apiErrorMessage(err, "Failed to create this task."),
        };
      }
    }

    setItems(updatedItems);
    setIsCreating(false);
    setIsConfirmOpen(false);

    setCreationResult({
      successCount,
      failCount,
      primaryProjectId:
        targetProjectIds.size > 0 ? Array.from(targetProjectIds)[0] : null,
    });

    if (successCount > 0 && onTasksCreated) {
      onTasksCreated({
        successCount,
        projectIds: Array.from(targetProjectIds),
      });
    }
  };

  return (
    <div
      className="note-task-suggestions"
      role="region"
      aria-label="AI Task Suggestions"
    >
      {/* Header */}
      <div className="note-task-suggestions__header">
        <div className="note-task-suggestions__title-group">
          <Sparkles
            size={16}
            className="note-task-suggestions__sparkle-icon"
            aria-hidden="true"
          />
          <h3 className="note-task-suggestions__title">AI Task Suggestions</h3>
          <span className="note-task-suggestions__badge">AI-Generated</span>
          {items.length > 0 && (
            <span className="note-task-suggestions__count-badge">
              {items.length} {items.length === 1 ? "task" : "tasks"} identified
            </span>
          )}
        </div>

        <div className="note-task-suggestions__header-actions">
          {onRegenerate && (
            <button
              type="button"
              className="note-task-suggestions__action-btn"
              onClick={onRegenerate}
              disabled={isLoading || isCreating}
              title="Regenerate suggestions"
              aria-label="Regenerate suggestions"
            >
              <RotateCw
                size={14}
                className={isLoading ? "note-task-suggestions__spin" : ""}
                aria-hidden="true"
              />
              <span>Regenerate</span>
            </button>
          )}
          {onClose && (
            <button
              type="button"
              className="note-task-suggestions__close-btn"
              onClick={onClose}
              disabled={isCreating}
              title="Dismiss suggestions"
              aria-label="Dismiss suggestions"
            >
              <X size={15} aria-hidden="true" />
            </button>
          )}
        </div>
      </div>

      {/* Loading state */}
      {isLoading && (
        <div className="note-task-suggestions__loading">
          <Spinner size="md" />
          <div className="note-task-suggestions__loading-text">
            <span>Analyzing note for actionable tasks...</span>
            <small>Scanning content, deadlines, priorities, and existing tasks</small>
          </div>
        </div>
      )}

      {/* Error state */}
      {!isLoading && error && (
        <div className="note-task-suggestions__error-banner" role="alert">
          <AlertCircle size={18} className="note-task-suggestions__error-icon" />
          <div className="note-task-suggestions__error-content">
            <span className="note-task-suggestions__error-title">
              Unable to analyze note
            </span>
            <span className="note-task-suggestions__error-desc">{error}</span>
          </div>
          {onRegenerate && (
            <Button
              variant="secondary"
              size="sm"
              onClick={onRegenerate}
              className="note-task-suggestions__retry-btn"
            >
              Try Again
            </Button>
          )}
        </div>
      )}

      {/* Empty result state */}
      {!isLoading && !error && items.length === 0 && (
        <div className="note-task-suggestions__empty">
          <ListTodo size={32} className="note-task-suggestions__empty-icon" />
          <h4 className="note-task-suggestions__empty-title">
            No actionable tasks were identified in this note.
          </h4>
          <p className="note-task-suggestions__empty-desc">
            The note contains background information, facts, or ideas, but no
            concrete actionable tasks were found.
          </p>
        </div>
      )}

      {/* Active suggestions list */}
      {!isLoading && !error && items.length > 0 && (
        <div className="note-task-suggestions__body">
          {/* Success Banner */}
          {creationResult && creationResult.successCount > 0 && (
            <div className="note-task-suggestions__success-banner">
              <CheckCircle2 size={18} className="note-task-suggestions__success-icon" />
              <div className="note-task-suggestions__success-text">
                <strong>
                  {creationResult.successCount}{" "}
                  {creationResult.successCount === 1 ? "task" : "tasks"} created
                  successfully.
                </strong>
                {creationResult.failCount > 0 && (
                  <span> ({creationResult.failCount} task(s) could not be created)</span>
                )}
              </div>
              <div className="note-task-suggestions__success-actions">
                <Link
                  to={
                    creationResult.primaryProjectId
                      ? `/projects/${creationResult.primaryProjectId}`
                      : "/tasks"
                  }
                  className="note-task-suggestions__view-link"
                >
                  <Button variant="secondary" size="sm">
                    <span>View Tasks</span>
                    <ExternalLink size={13} aria-hidden="true" />
                  </Button>
                </Link>
              </div>
            </div>
          )}

          {/* Validation error message */}
          {validationError && (
            <div className="note-task-suggestions__validation-error" role="alert">
              <AlertTriangle size={15} />
              <span>{validationError}</span>
            </div>
          )}

          {/* Global batch toolbar */}
          <div className="note-task-suggestions__toolbar">
            <div className="note-task-suggestions__selection-controls">
              <button
                type="button"
                className="note-task-suggestions__text-btn"
                onClick={() => handleSelectAll(true)}
                disabled={isCreating}
              >
                Select All
              </button>
              <span className="note-task-suggestions__divider">|</span>
              <button
                type="button"
                className="note-task-suggestions__text-btn"
                onClick={() => handleSelectAll(false)}
                disabled={isCreating}
              >
                Deselect All
              </button>
              <span className="note-task-suggestions__selected-count">
                ({selectedCount} of {items.length} selected)
              </span>
            </div>

            {/* Default / Batch Project selector */}
            <div className="note-task-suggestions__batch-project">
              <label
                htmlFor="batch-project-select"
                className="note-task-suggestions__batch-label"
              >
                <FolderKanban size={13} aria-hidden="true" />
                <span>Target Project:</span>
              </label>
              <select
                id="batch-project-select"
                className="note-task-suggestions__select"
                value={batchProjectId}
                onChange={(e) => handleBatchProjectChange(e.target.value)}
                disabled={isCreating || isLoadingProjects}
              >
                <option value="">-- Select Project for Tasks --</option>
                {projects.map((proj) => (
                  <option key={proj.id} value={String(proj.id)}>
                    {proj.name}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Items list */}
          <div className="note-task-suggestions__list">
            {items.map((item) => {
              const isCreated = item.status === "created";
              const isError = item.status === "error";
              const isExpanded = Boolean(expandedDetails[item.id]);
              const showDuplicateWarning =
                item.is_duplicate && !item.duplicate_dismissed && !isCreated;

              return (
                <div
                  key={item.id}
                  className={`note-task-suggestions__item ${
                    item.selected ? "note-task-suggestions__item--selected" : ""
                  } ${isCreated ? "note-task-suggestions__item--created" : ""} ${
                    showDuplicateWarning
                      ? "note-task-suggestions__item--duplicate"
                      : ""
                  }`}
                >
                  {/* Item header: Checkbox + Title input + Quick status */}
                  <div className="note-task-suggestions__item-row">
                    <label className="note-task-suggestions__checkbox-wrap">
                      <input
                        type="checkbox"
                        checked={item.selected}
                        onChange={() => handleToggleSelect(item.id)}
                        disabled={isCreated || isCreating}
                        className="note-task-suggestions__checkbox"
                        aria-label={`Select task: ${item.title}`}
                      />
                    </label>

                    <div className="note-task-suggestions__item-title-col">
                      {isCreated ? (
                        <div className="note-task-suggestions__created-title">
                          <CheckCircle2 size={16} className="text-success" />
                          <span>{item.title}</span>
                          <Badge variant="success">Created</Badge>
                        </div>
                      ) : (
                        <input
                          type="text"
                          className="note-task-suggestions__title-input"
                          value={item.title}
                          onChange={(e) =>
                            handleUpdateItem(item.id, "title", e.target.value)
                          }
                          disabled={isCreating}
                          placeholder="Task title..."
                        />
                      )}
                    </div>

                    <div className="note-task-suggestions__item-badges">
                      <span
                        className={`note-task-suggestions__priority-tag note-task-suggestions__priority-tag--${item.priority}`}
                      >
                        <Flag size={11} aria-hidden="true" />
                        <span>{item.priority}</span>
                      </span>

                      {item.confidence !== undefined && (
                        <span
                          className="note-task-suggestions__confidence-tag"
                          title="AI confidence score"
                        >
                          {Math.round(item.confidence * 100)}%
                        </span>
                      )}

                      <button
                        type="button"
                        className="note-task-suggestions__expand-btn"
                        onClick={() => toggleExpand(item.id)}
                        title={isExpanded ? "Hide details" : "Edit details"}
                        aria-label="Toggle details"
                      >
                        {isExpanded ? <ChevronUp size={15} /> : <ChevronDown size={15} />}
                      </button>
                    </div>
                  </div>

                  {/* Duplicate warning callout */}
                  {showDuplicateWarning && (
                    <div
                      className="note-task-suggestions__duplicate-callout"
                      role="alert"
                    >
                      <AlertTriangle size={14} className="text-warning" />
                      <div className="note-task-suggestions__duplicate-text">
                        <strong>Possible duplicate:</strong> An existing task with
                        a similar title already exists (
                        <em>"{item.duplicate_task_title}"</em>).
                      </div>
                      <div className="note-task-suggestions__duplicate-actions">
                        <button
                          type="button"
                          className="note-task-suggestions__dup-btn note-task-suggestions__dup-btn--skip"
                          onClick={() => handleSkipDuplicate(item.id)}
                        >
                          Skip
                        </button>
                        <button
                          type="button"
                          className="note-task-suggestions__dup-btn note-task-suggestions__dup-btn--create"
                          onClick={() => handleDismissDuplicate(item.id)}
                        >
                          Create Anyway
                        </button>
                      </div>
                    </div>
                  )}

                  {/* Item error if creation failed */}
                  {isError && item.errorMessage && (
                    <div className="note-task-suggestions__item-error">
                      <AlertCircle size={13} />
                      <span>{item.errorMessage}</span>
                    </div>
                  )}

                  {/* Reason summary */}
                  {item.reason && (
                    <div className="note-task-suggestions__reason">
                      <span className="note-task-suggestions__reason-label">
                        Reason:
                      </span>
                      <span>{item.reason}</span>
                    </div>
                  )}

                  {/* Editable Fields / Details (collapsible or always open if expanded) */}
                  {isExpanded && !isCreated && (
                    <div className="note-task-suggestions__details-grid">
                      {/* Description */}
                      <div className="note-task-suggestions__field note-task-suggestions__field--full">
                        <label className="note-task-suggestions__field-label">
                          Description
                        </label>
                        <textarea
                          className="note-task-suggestions__textarea"
                          rows={2}
                          value={item.description}
                          onChange={(e) =>
                            handleUpdateItem(
                              item.id,
                              "description",
                              e.target.value
                            )
                          }
                          disabled={isCreating}
                          placeholder="Task description / notes..."
                        />
                      </div>

                      {/* Priority */}
                      <div className="note-task-suggestions__field">
                        <label className="note-task-suggestions__field-label">
                          <Flag size={12} aria-hidden="true" />
                          <span>Priority</span>
                        </label>
                        <select
                          className="note-task-suggestions__select"
                          value={item.priority}
                          onChange={(e) =>
                            handleUpdateItem(item.id, "priority", e.target.value)
                          }
                          disabled={isCreating}
                        >
                          {PRIORITY_OPTIONS.map((opt) => (
                            <option key={opt.value} value={opt.value}>
                              {opt.label}
                            </option>
                          ))}
                        </select>
                      </div>

                      {/* Due Date */}
                      <div className="note-task-suggestions__field">
                        <label className="note-task-suggestions__field-label">
                          <Calendar size={12} aria-hidden="true" />
                          <span>Due Date</span>
                        </label>
                        <input
                          type="date"
                          className="note-task-suggestions__date-input"
                          value={item.due_date}
                          onChange={(e) =>
                            handleUpdateItem(item.id, "due_date", e.target.value)
                          }
                          disabled={isCreating}
                        />
                      </div>

                      {/* Target Project */}
                      <div className="note-task-suggestions__field">
                        <label className="note-task-suggestions__field-label">
                          <FolderKanban size={12} aria-hidden="true" />
                          <span>Project</span>
                        </label>
                        <select
                          className="note-task-suggestions__select"
                          value={item.projectId}
                          onChange={(e) =>
                            handleUpdateItem(
                              item.id,
                              "projectId",
                              e.target.value
                            )
                          }
                          disabled={isCreating || isLoadingProjects}
                        >
                          <option value="">-- Choose Project --</option>
                          {projects.map((p) => (
                            <option key={p.id} value={String(p.id)}>
                              {p.name}
                            </option>
                          ))}
                        </select>
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>

          {/* Action footer */}
          <div className="note-task-suggestions__footer">
            <div className="note-task-suggestions__footer-hint">
              <span>
                {selectedCount}{" "}
                {selectedCount === 1 ? "task" : "tasks"} selected for creation
              </span>
              {createdCount > 0 && (
                <span className="note-task-suggestions__created-count">
                  ({createdCount} already created)
                </span>
              )}
            </div>

            <Button
              variant="primary"
              onClick={handleInitiateCreation}
              disabled={selectedCount === 0 || isCreating}
            >
              {isCreating ? (
                <>
                  <Spinner size="sm" />
                  <span>Creating Tasks...</span>
                </>
              ) : (
                <>
                  <ListTodo size={15} aria-hidden="true" />
                  <span>Create Selected Tasks ({selectedCount})</span>
                </>
              )}
            </Button>
          </div>
        </div>
      )}

      {/* Confirmation Modal */}
      <Modal
        open={isConfirmOpen}
        onClose={() => {
          if (!isCreating) setIsConfirmOpen(false);
        }}
        title="Confirm Task Creation"
      >
        <div className="note-task-suggestions__confirm-body">
          <p className="note-task-suggestions__confirm-lead">
            Create <strong>{selectedCount}</strong> selected{" "}
            {selectedCount === 1 ? "task" : "tasks"}?
          </p>
          <p className="note-task-suggestions__confirm-sub">
            These tasks will be added to TaskForge AI under their selected
            projects. You can view, track, and manage them anytime.
          </p>

          <div className="note-task-suggestions__confirm-preview-list">
            {selectedItems.map((item) => {
              const proj = projects.find((p) => String(p.id) === String(item.projectId));
              return (
                <div
                  key={item.id}
                  className="note-task-suggestions__confirm-item"
                >
                  <div className="note-task-suggestions__confirm-item-main">
                    <span className="note-task-suggestions__confirm-title">
                      {item.title}
                    </span>
                    <span className="note-task-suggestions__confirm-meta">
                      {proj ? proj.name : "No Project Selected"}
                      {item.due_date ? ` • Due: ${item.due_date}` : ""}
                    </span>
                  </div>
                  <span
                    className={`note-task-suggestions__priority-tag note-task-suggestions__priority-tag--${item.priority}`}
                  >
                    {item.priority}
                  </span>
                </div>
              );
            })}
          </div>

          <div className="note-task-suggestions__confirm-actions">
            <Button
              variant="secondary"
              onClick={() => setIsConfirmOpen(false)}
              disabled={isCreating}
            >
              Cancel
            </Button>
            <Button
              variant="primary"
              onClick={handleConfirmCreate}
              disabled={isCreating}
            >
              {isCreating ? (
                <>
                  <Spinner size="sm" />
                  <span>Creating...</span>
                </>
              ) : (
                <span>Create Tasks</span>
              )}
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}

export default NoteTaskSuggestions;
