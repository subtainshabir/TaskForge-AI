import { useState, useEffect } from "react";
import {
  AlertCircle,
  ArrowRight,
  Check,
  CheckCircle2,
  RefreshCw,
  Sparkles,
  X,
} from "lucide-react";
import Modal from "../../Modal/Modal.jsx";
import Button from "../../Button/Button.jsx";
import Spinner from "../../Spinner/Spinner.jsx";
import Badge from "../../Badge/Badge.jsx";
import Textarea from "../../Textarea/Textarea.jsx";
import { taskService } from "../../../services/taskService.js";
import { apiErrorMessage } from "../../../utils/apiErrorMessage.js";
import "./TaskAIRegenerateModal.css";

const QUICK_INSTRUCTIONS = [
  "Make it more specific",
  "Add acceptance criteria",
  "Make it more actionable",
  "Suitable for backend developer",
];

function TaskAIRegenerateModal({ open, onClose, task, onTaskUpdated }) {
  const [instruction, setInstruction] = useState("");
  const [proposal, setProposal] = useState(null);
  const [isGenerating, setIsGenerating] = useState(false);
  const [isApplying, setIsApplying] = useState(false);
  const [error, setError] = useState("");

  // Reset state when modal opens
  useEffect(() => {
    if (open) {
      setProposal(null);
      setError("");
      setInstruction("");
    }
  }, [open]);

  const handleGenerate = async (customInst) => {
    if (!task || isGenerating) return;
    setIsGenerating(true);
    setError("");

    const instToSend = typeof customInst === "string" ? customInst : instruction;

    try {
      const data = await taskService.regenerateWithAI(task.id, instToSend);
      setProposal(data);
    } catch (err) {
      setError(
        apiErrorMessage(
          err,
          "Failed to generate task improvement proposal. Please check your AI configuration and try again."
        )
      );
    } finally {
      setIsGenerating(false);
    }
  };

  const handleApply = async () => {
    if (!task || !proposal || isApplying) return;
    setIsApplying(true);
    setError("");

    try {
      const updated = await taskService.update(task.id, {
        title: proposal.title,
        description: proposal.description,
      });

      if (onTaskUpdated) {
        onTaskUpdated(updated);
      }
      onClose();
    } catch (err) {
      setError(apiErrorMessage(err, "Failed to apply proposed task improvements."));
    } finally {
      setIsApplying(false);
    }
  };

  const handleDiscard = () => {
    setProposal(null);
    setError("");
    onClose();
  };

  const handleQuickInstruction = (qi) => {
    setInstruction(qi);
    handleGenerate(qi);
  };

  if (!open || !task) return null;

  return (
    <Modal
      open={open}
      onClose={isGenerating || isApplying ? undefined : handleDiscard}
      title={proposal ? "AI Task Improvement Proposal" : "Improve this task with AI"}
    >
      <div className="task-ai-regen">
        {error && (
          <div className="task-ai-regen__error" role="alert">
            <div className="task-ai-regen__error-content">
              <AlertCircle size={16} aria-hidden="true" />
              <span>{error}</span>
            </div>
            <div className="task-ai-regen__error-actions">
              <Button
                variant="secondary"
                size="sm"
                onClick={() => handleGenerate(instruction)}
                disabled={isGenerating || isApplying}
              >
                Try again
              </Button>
              <button
                type="button"
                className="task-ai-regen__dismiss-btn"
                onClick={() => setError("")}
                aria-label="Dismiss error"
              >
                <X size={14} aria-hidden="true" />
              </button>
            </div>
          </div>
        )}

        {isGenerating ? (
          <div className="task-ai-regen__loading" role="status" aria-live="polite">
            <Spinner size="md" label="Improving task" />
            <p className="task-ai-regen__loading-title">AI is improving your task...</p>
            <p className="task-ai-regen__loading-subtext">
              Analyzing context, refining scope, and formulating clear acceptance criteria...
            </p>
          </div>
        ) : proposal ? (
          /* PREVIEW STATE */
          <div className="task-ai-regen__preview">
            <div className="task-ai-regen__comparison">
              {/* ORIGINAL TASK */}
              <div className="task-ai-regen__compare-col task-ai-regen__compare-col--original">
                <div className="task-ai-regen__col-header">
                  <span className="task-ai-regen__col-label">Current Task</span>
                  <Badge variant="neutral">Original</Badge>
                </div>
                <div className="task-ai-regen__field">
                  <span className="task-ai-regen__field-label">Title</span>
                  <p className="task-ai-regen__field-value task-ai-regen__field-value--dim">
                    {task.title}
                  </p>
                </div>
                <div className="task-ai-regen__field">
                  <span className="task-ai-regen__field-label">Description</span>
                  <p className="task-ai-regen__field-value task-ai-regen__field-value--dim">
                    {task.description || "(No description provided)"}
                  </p>
                </div>
              </div>

              {/* PROPOSED TASK */}
              <div className="task-ai-regen__compare-col task-ai-regen__compare-col--proposed">
                <div className="task-ai-regen__col-header">
                  <span className="task-ai-regen__col-label">AI Proposal</span>
                  <Badge variant="ai">Improved</Badge>
                </div>
                <div className="task-ai-regen__field">
                  <span className="task-ai-regen__field-label">Suggested Title</span>
                  <p className="task-ai-regen__field-value task-ai-regen__field-value--highlight">
                    {proposal.title}
                  </p>
                </div>
                <div className="task-ai-regen__field">
                  <span className="task-ai-regen__field-label">Suggested Description</span>
                  <p className="task-ai-regen__field-value task-ai-regen__field-value--highlight">
                    {proposal.description}
                  </p>
                </div>

                {proposal.changes && proposal.changes.length > 0 && (
                  <div className="task-ai-regen__changes">
                    <span className="task-ai-regen__changes-title">Improvements Made:</span>
                    <ul className="task-ai-regen__changes-list">
                      {proposal.changes.map((change, idx) => (
                        <li key={idx} className="task-ai-regen__changes-item">
                          <CheckCircle2 size={13} className="task-ai-regen__change-icon" aria-hidden="true" />
                          <span>{change}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            </div>

            {/* ACTION BAR */}
            <div className="task-ai-regen__actions">
              <Button
                variant="primary"
                onClick={handleApply}
                disabled={isApplying}
              >
                {isApplying ? (
                  <>
                    <Spinner size="sm" label="Applying changes" />
                    Applying changes...
                  </>
                ) : (
                  <>
                    <Check size={16} aria-hidden="true" />
                    Apply Changes
                  </>
                )}
              </Button>

              <Button
                variant="secondary"
                onClick={() => handleGenerate(instruction)}
                disabled={isApplying}
              >
                <RefreshCw size={14} aria-hidden="true" />
                Regenerate Again
              </Button>

              <Button
                variant="secondary"
                onClick={handleDiscard}
                disabled={isApplying}
              >
                Discard
              </Button>
            </div>
          </div>
        ) : (
          /* INITIAL / INSTRUCTION STATE */
          <div className="task-ai-regen__initial">
            <div className="task-ai-regen__current-summary">
              <span className="task-ai-regen__context-label">Current Task:</span>
              <p className="task-ai-regen__current-title">{task.title}</p>
              {task.description && (
                <p className="task-ai-regen__current-desc">{task.description}</p>
              )}
            </div>

            <div className="task-ai-regen__prompt-box">
              <label htmlFor="regen-instruction" className="task-ai-regen__input-label">
                How should AI improve this task? (optional)
              </label>
              <Textarea
                id="regen-instruction"
                rows={3}
                placeholder="e.g., Make this task clearer and more actionable, define specific acceptance criteria, or make it suitable for a backend engineer..."
                value={instruction}
                onChange={(e) => setInstruction(e.target.value)}
                disabled={isGenerating}
              />

              <div className="task-ai-regen__quick-chips">
                <span className="task-ai-regen__chips-label">Quick guidance:</span>
                <div className="task-ai-regen__chips-group">
                  {QUICK_INSTRUCTIONS.map((qi) => (
                    <button
                      key={qi}
                      type="button"
                      className="task-ai-regen__chip"
                      onClick={() => handleQuickInstruction(qi)}
                      disabled={isGenerating}
                    >
                      {qi}
                    </button>
                  ))}
                </div>
              </div>
            </div>

            <div className="task-ai-regen__actions">
              <Button
                variant="primary"
                onClick={() => handleGenerate(instruction)}
                disabled={isGenerating}
              >
                <Sparkles size={16} aria-hidden="true" />
                Improve Task with AI
              </Button>

              <Button
                variant="secondary"
                onClick={handleDiscard}
                disabled={isGenerating}
              >
                Cancel
              </Button>
            </div>
          </div>
        )}
      </div>
    </Modal>
  );
}

export default TaskAIRegenerateModal;
