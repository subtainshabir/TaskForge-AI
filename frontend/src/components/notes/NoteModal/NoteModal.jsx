import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  FolderKanban,
  CheckSquare,
  Clock,
  Calendar,
  Pencil,
  Trash2,
  ExternalLink,
  Sparkles,
  FileSearch,
  ListTodo,
  MessageSquare,
} from "lucide-react";
import Modal from "../../Modal/Modal.jsx";
import Button from "../../Button/Button.jsx";
import Badge from "../../Badge/Badge.jsx";
import RichTextViewer from "../RichTextViewer/RichTextViewer.jsx";
import NoteAISummary from "../NoteAISummary/NoteAISummary.jsx";
import NoteExtractionResult from "../NoteExtractionResult/NoteExtractionResult.jsx";
import NoteTaskSuggestions from "../NoteTaskSuggestions/NoteTaskSuggestions.jsx";
import NoteAIImprovement from "../NoteAIImprovement/NoteAIImprovement.jsx";
import NoteAIChat from "../NoteAIChat/NoteAIChat.jsx";
import { noteService } from "../../../services/noteService.js";
import { apiErrorMessage } from "../../../utils/apiErrorMessage.js";
import { formatAbsoluteDate, formatActivityTime } from "../../../utils/date.js";
import "./NoteModal.css";

function NoteModal({
  note,
  open,
  onClose,
  onEdit,
  onDelete,
  onCheckboxToggle,
  onNoteUpdated,
}) {
  const [aiSummary, setAiSummary] = useState(null);
  const [isSummarizing, setIsSummarizing] = useState(false);
  const [summaryError, setSummaryError] = useState("");

  const [aiExtraction, setAiExtraction] = useState(null);
  const [isExtracting, setIsExtracting] = useState(false);
  const [extractionError, setExtractionError] = useState("");

  const [aiTaskSuggestions, setAiTaskSuggestions] = useState(null);
  const [isSuggestingTasks, setIsSuggestingTasks] = useState(false);
  const [taskSuggestionsError, setTaskSuggestionsError] = useState("");

  const [aiImprovement, setAiImprovement] = useState(null);
  const [isImproving, setIsImproving] = useState(false);
  const [improvementError, setImprovementError] = useState("");
  const [isApplyingImprovement, setIsApplyingImprovement] = useState(false);

  const [isChatOpen, setIsChatOpen] = useState(false);

  // Reset summary, extraction, task suggestions, and improvement state when opening a different note
  useEffect(() => {
    setAiSummary(null);
    setIsSummarizing(false);
    setSummaryError("");
    setAiExtraction(null);
    setIsExtracting(false);
    setExtractionError("");
    setAiTaskSuggestions(null);
    setIsSuggestingTasks(false);
    setTaskSuggestionsError("");
    setAiImprovement(null);
    setIsImproving(false);
    setImprovementError("");
    setIsApplyingImprovement(false);
    setIsChatOpen(false);
  }, [note?.id]);

  async function handleSummarize() {
    if (!note?.id) return;
    setIsSummarizing(true);
    setSummaryError("");
    try {
      const result = await noteService.summarizeWithAI(note.id);
      setAiSummary(result);
    } catch (err) {
      setSummaryError(apiErrorMessage(err, "Failed to generate AI summary."));
    } finally {
      setIsSummarizing(false);
    }
  }

  async function handleExtract() {
    if (!note?.id) return;
    setIsExtracting(true);
    setExtractionError("");
    try {
      const result = await noteService.extractWithAI(note.id);
      setAiExtraction(result);
    } catch (err) {
      setExtractionError(apiErrorMessage(err, "Failed to extract information with AI."));
    } finally {
      setIsExtracting(false);
    }
  }

  async function handleSuggestTasks() {
    if (!note?.id) return;
    setIsSuggestingTasks(true);
    setTaskSuggestionsError("");
    try {
      const result = await noteService.suggestTasksWithAI(note.id);
      setAiTaskSuggestions(result);
    } catch (err) {
      setTaskSuggestionsError(
        apiErrorMessage(err, "Failed to analyze note for task suggestions.")
      );
    } finally {
      setIsSuggestingTasks(false);
    }
  }

  async function handleImprove() {
    if (!note?.id) return;
    setIsImproving(true);
    setImprovementError("");
    try {
      const hasContent = Boolean(
        (note?.content && note.content.trim().length >= 10) ||
        (note?.title && note.title.trim().length >= 10)
      );
      if (!hasContent) {
        setImprovementError("This note does not contain enough content to improve yet.");
        setIsImproving(false);
        return;
      }
      const result = await noteService.improveWithAI(note.id);
      setAiImprovement(result);
    } catch (err) {
      setImprovementError(apiErrorMessage(err, "Failed to review note with AI."));
    } finally {
      setIsImproving(false);
    }
  }

  async function handleApplyImprovement(improvedTitle, improvedContent) {
    if (!note?.id) return;
    setIsApplyingImprovement(true);
    setImprovementError("");
    try {
      const updated = await noteService.update(note.id, {
        title: improvedTitle,
        content: improvedContent,
      });
      if (onNoteUpdated) {
        onNoteUpdated(updated);
      }
      setAiImprovement(null);
    } catch (err) {
      setImprovementError(apiErrorMessage(err, "Failed to apply AI improvements."));
    } finally {
      setIsApplyingImprovement(false);
    }
  }
  if (!note) return null;

  const hasProject = Boolean(note.project_id);
  const hasTask = Boolean(note.task_id);

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={note.title}
      footer={
        <div className="note-modal__footer-actions">
          <Link
            to={`/notes/${note.id}`}
            className="note-modal__full-page-link"
            title="Open dedicated note page"
          >
            <ExternalLink size={14} aria-hidden="true" />
            <span>Dedicated page</span>
          </Link>
          <div className="note-modal__right-actions">
            <Button
              type="button"
              variant="secondary"
              className="note-modal__ai-btn"
              disabled={isSummarizing || isExtracting || isSuggestingTasks}
              loading={isSummarizing}
              onClick={handleSummarize}
            >
              <Sparkles size={14} aria-hidden="true" />
              Summarize
            </Button>
            <Button
              type="button"
              variant="secondary"
              className="note-modal__ai-btn"
              disabled={isExtracting || isSummarizing || isSuggestingTasks}
              loading={isExtracting}
              onClick={handleExtract}
              title="Extract structured information with AI"
            >
              <FileSearch size={14} aria-hidden="true" />
              Extract
            </Button>
            <Button
              type="button"
              variant="secondary"
              className="note-modal__ai-btn"
              disabled={isSuggestingTasks || isSummarizing || isExtracting || isImproving}
              loading={isSuggestingTasks}
              onClick={handleSuggestTasks}
              title="Suggest actionable tasks from this note with AI"
            >
              <ListTodo size={14} aria-hidden="true" />
              Suggest Tasks
            </Button>
            <Button
              type="button"
              variant="secondary"
              className="note-modal__ai-btn"
              disabled={isImproving || isSummarizing || isExtracting || isSuggestingTasks}
              loading={isImproving}
              onClick={handleImprove}
              title="Improve clarity, structure, and grammar with AI"
            >
              <Sparkles size={14} aria-hidden="true" />
              Improve
            </Button>
            <Button
              type="button"
              variant={isChatOpen ? "primary" : "secondary"}
              className="note-modal__ai-btn"
              disabled={isImproving || isSummarizing || isExtracting || isSuggestingTasks}
              onClick={() => setIsChatOpen((prev) => !prev)}
              title="Ask questions about this note with AI"
            >
              <MessageSquare size={14} aria-hidden="true" />
              Ask AI
            </Button>
            {onDelete && (
              <Button
                type="button"
                variant="ghost"
                onClick={() => {
                  onClose();
                  onDelete(note);
                }}
              >
                <Trash2 size={15} aria-hidden="true" />
                Delete
              </Button>
            )}
            {onEdit && (
              <Button
                type="button"
                variant="secondary"
                onClick={() => {
                  onClose();
                  onEdit(note);
                }}
              >
                <Pencil size={15} aria-hidden="true" />
                Edit
              </Button>
            )}
            <Button type="button" variant="primary" onClick={onClose}>
              Done
            </Button>
          </div>
        </div>
      }
    >
      <div className="note-modal__meta">
        <div className="note-modal__associations">
          {hasProject && (
            <Link
              to={`/projects/${note.project_id}`}
              className="note-modal__badge-link"
            >
              <Badge variant="neutral">
                <FolderKanban size={13} aria-hidden="true" />
                <span>{note.project_name || `Project #${note.project_id}`}</span>
              </Badge>
            </Link>
          )}

          {hasTask && (
            <Link
              to={
                note.project_id
                  ? `/projects/${note.project_id}/tasks/${note.task_id}`
                  : `/tasks`
              }
              className="note-modal__badge-link"
            >
              <Badge variant="neutral" className="note-modal__task-badge">
                <CheckSquare size={13} aria-hidden="true" />
                <span>{note.task_title || `Task #${note.task_id}`}</span>
              </Badge>
            </Link>
          )}

          {!hasProject && !hasTask && (
            <span className="note-modal__general-badge">General Note</span>
          )}
        </div>

        <div className="note-modal__timestamps">
          <span title={`Created on ${formatAbsoluteDate(note.created_at)}`}>
            <Calendar size={13} aria-hidden="true" />
            Created {formatAbsoluteDate(note.created_at)}
          </span>
          <span title={`Updated ${formatActivityTime(note.updated_at)}`}>
            <Clock size={13} aria-hidden="true" />
            Updated {formatActivityTime(note.updated_at)}
          </span>
        </div>
      </div>

      <NoteAISummary
        summary={aiSummary}
        isLoading={isSummarizing}
        error={summaryError}
        onRegenerate={handleSummarize}
        onClose={() => {
          setAiSummary(null);
          setSummaryError("");
        }}
      />

      <NoteExtractionResult
        extraction={aiExtraction}
        isLoading={isExtracting}
        error={extractionError}
        onRegenerate={handleExtract}
        onClose={() => {
          setAiExtraction(null);
          setExtractionError("");
        }}
      />

      <NoteTaskSuggestions
        suggestionsData={aiTaskSuggestions}
        isLoading={isSuggestingTasks}
        error={taskSuggestionsError}
        onRegenerate={handleSuggestTasks}
        onClose={() => {
          setAiTaskSuggestions(null);
          setTaskSuggestionsError("");
        }}
        currentNote={note}
      />

      <NoteAIImprovement
        originalNote={note}
        improvement={aiImprovement}
        isLoading={isImproving}
        error={improvementError}
        isApplying={isApplyingImprovement}
        onRegenerate={handleImprove}
        onKeepOriginal={() => {
          setAiImprovement(null);
          setImprovementError("");
        }}
        onClose={() => {
          setAiImprovement(null);
          setImprovementError("");
        }}
        onApply={handleApplyImprovement}
      />

      <NoteAIChat
        note={note}
        open={isChatOpen}
        onClose={() => setIsChatOpen(false)}
      />

      <div className="note-modal__content">
        <RichTextViewer
          content={note.content}
          onCheckboxToggle={onCheckboxToggle}
          emptyMessage="No additional content in this note."
        />
      </div>
    </Modal>
  );
}

export default NoteModal;
