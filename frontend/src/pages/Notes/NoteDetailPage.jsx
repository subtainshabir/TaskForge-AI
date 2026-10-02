import { useCallback, useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import {
  ArrowLeft,
  Calendar,
  CheckSquare,
  Clock,
  FolderKanban,
  Pencil,
  Trash2,
  StickyNote,
  Sparkles,
  FileSearch,
  ListTodo,
  MessageSquare,
} from "lucide-react";
import PageContainer from "../../components/PageContainer/PageContainer.jsx";
import Card from "../../components/Card/Card.jsx";
import Badge from "../../components/Badge/Badge.jsx";
import Button from "../../components/Button/Button.jsx";
import Modal from "../../components/Modal/Modal.jsx";
import Spinner from "../../components/Spinner/Spinner.jsx";
import { ErrorState } from "../../components/StatePanel/StatePanel.jsx";
import NoteForm from "../../components/notes/NoteForm/NoteForm.jsx";
import DeleteNoteDialog from "../../components/notes/DeleteNoteDialog/DeleteNoteDialog.jsx";
import RichTextViewer from "../../components/notes/RichTextViewer/RichTextViewer.jsx";
import NoteAISummary from "../../components/notes/NoteAISummary/NoteAISummary.jsx";
import NoteExtractionResult from "../../components/notes/NoteExtractionResult/NoteExtractionResult.jsx";
import NoteTaskSuggestions from "../../components/notes/NoteTaskSuggestions/NoteTaskSuggestions.jsx";
import NoteAIImprovement from "../../components/notes/NoteAIImprovement/NoteAIImprovement.jsx";
import NoteAIChat from "../../components/notes/NoteAIChat/NoteAIChat.jsx";
import { noteService } from "../../services/noteService.js";
import { apiErrorMessage } from "../../utils/apiErrorMessage.js";
import { formatAbsoluteDate, formatActivityTime } from "../../utils/date.js";
import "./NoteDetailPage.css";

function NoteDetailPage() {
  const { noteId } = useParams();
  const navigate = useNavigate();

  const [note, setNote] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");

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

  const [isEditOpen, setIsEditOpen] = useState(false);
  const [isDeleteOpen, setIsDeleteOpen] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [formError, setFormError] = useState("");
  const [deleteError, setDeleteError] = useState("");

  const loadNote = useCallback(async () => {
    setIsLoading(true);
    setError("");
    setAiSummary(null);
    setSummaryError("");
    setAiExtraction(null);
    setExtractionError("");
    setAiTaskSuggestions(null);
    setTaskSuggestionsError("");
    setAiImprovement(null);
    setIsImproving(false);
    setImprovementError("");
    setIsApplyingImprovement(false);
    setIsChatOpen(false);
    try {
      const data = await noteService.get(noteId);
      setNote(data);
    } catch (err) {
      setError(
        apiErrorMessage(
          err,
          "This note doesn't exist or you don't have permission to access it."
        )
      );
    } finally {
      setIsLoading(false);
    }
  }, [noteId]);

  useEffect(() => {
    loadNote();
  }, [loadNote]);

  async function handleSummarize() {
    setIsSummarizing(true);
    setSummaryError("");
    try {
      const summary = await noteService.summarizeWithAI(noteId);
      setAiSummary(summary);
    } catch (err) {
      setSummaryError(apiErrorMessage(err, "Failed to generate AI summary."));
    } finally {
      setIsSummarizing(false);
    }
  }

  async function handleExtract() {
    setIsExtracting(true);
    setExtractionError("");
    try {
      const result = await noteService.extractWithAI(noteId);
      setAiExtraction(result);
    } catch (err) {
      setExtractionError(apiErrorMessage(err, "Failed to extract information with AI."));
    } finally {
      setIsExtracting(false);
    }
  }

  async function handleSuggestTasks() {
    setIsSuggestingTasks(true);
    setTaskSuggestionsError("");
    try {
      const result = await noteService.suggestTasksWithAI(noteId);
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
    setIsImproving(true);
    setImprovementError("");
    try {
      // Empty content check in frontend (Section 12)
      const hasContent = Boolean(
        (note?.content && note.content.trim().length >= 10) ||
        (note?.title && note.title.trim().length >= 10)
      );
      if (!hasContent) {
        setImprovementError("This note does not contain enough content to improve yet.");
        setIsImproving(false);
        return;
      }
      const result = await noteService.improveWithAI(noteId);
      setAiImprovement(result);
    } catch (err) {
      setImprovementError(apiErrorMessage(err, "Failed to review note with AI."));
    } finally {
      setIsImproving(false);
    }
  }

  async function handleApplyImprovement(improvedTitle, improvedContent) {
    setIsApplyingImprovement(true);
    setImprovementError("");
    try {
      const updated = await noteService.update(noteId, {
        title: improvedTitle,
        content: improvedContent,
      });
      setNote(updated);
      setAiImprovement(null);
    } catch (err) {
      setImprovementError(apiErrorMessage(err, "Failed to apply AI improvements."));
    } finally {
      setIsApplyingImprovement(false);
    }
  }

  async function handleUpdate(payload) {
    setIsSaving(true);
    setFormError("");
    try {
      const updated = await noteService.update(noteId, payload);
      setNote(updated);
      setIsEditOpen(false);
    } catch (err) {
      setFormError(apiErrorMessage(err, "Failed to update note."));
    } finally {
      setIsSaving(false);
    }
  }

  async function handleDelete() {
    setIsDeleting(true);
    setDeleteError("");
    try {
      await noteService.remove(noteId);
      navigate("/notes", { replace: true });
    } catch (err) {
      setDeleteError(apiErrorMessage(err, "Failed to delete note."));
    } finally {
      setIsDeleting(false);
    }
  }

  async function handleCheckboxToggle(updatedContent) {
    try {
      const updated = await noteService.update(noteId, { content: updatedContent });
      setNote(updated);
    } catch {
      // Ignore background sync failure
    }
  }

  if (isLoading) {
    return (
      <PageContainer>
        <div className="note-detail__loading">
          <Spinner size="lg" label="Loading note details..." />
        </div>
      </PageContainer>
    );
  }

  if (error || !note) {
    return (
      <PageContainer>
        <Card>
          <ErrorState
            title="Note not found"
            description={
              error ||
              "This note doesn't exist or you don't have access to view it."
            }
            action={
              <Button variant="secondary" onClick={() => navigate("/notes")}>
                Back to Notes
              </Button>
            }
          />
        </Card>
      </PageContainer>
    );
  }

  const hasProject = Boolean(note.project_id);
  const hasTask = Boolean(note.task_id);

  return (
    <PageContainer
      title={note.title}
      actions={
        <div className="note-detail__actions">
          <Button
            variant="secondary"
            className="note-detail__ai-btn"
            onClick={handleSummarize}
            disabled={isSummarizing || isExtracting || isSuggestingTasks}
            title="Summarize this note with AI"
          >
            {isSummarizing ? (
              <Spinner size="sm" />
            ) : (
              <Sparkles size={16} aria-hidden="true" className="note-detail__ai-icon" />
            )}
            <span>{isSummarizing ? "Summarizing..." : "Summarize with AI"}</span>
          </Button>
          <Button
            variant="secondary"
            className="note-detail__ai-btn"
            onClick={handleExtract}
            disabled={isExtracting || isSummarizing || isSuggestingTasks}
            title="Extract structured information with AI"
          >
            {isExtracting ? (
              <Spinner size="sm" />
            ) : (
              <FileSearch size={16} aria-hidden="true" className="note-detail__ai-icon" />
            )}
            <span>{isExtracting ? "Extracting..." : "Extract with AI"}</span>
          </Button>
          <Button
            variant="secondary"
            className="note-detail__ai-btn note-detail__ai-btn--suggest"
            onClick={handleSuggestTasks}
            disabled={isSuggestingTasks || isSummarizing || isExtracting}
            title="Suggest actionable tasks from this note with AI"
          >
            {isSuggestingTasks ? (
              <Spinner size="sm" />
            ) : (
              <ListTodo size={16} aria-hidden="true" className="note-detail__ai-icon" />
            )}
            <span>{isSuggestingTasks ? "Analyzing..." : "Suggest Tasks"}</span>
          </Button>
          <Button
            variant="secondary"
            className="note-detail__ai-btn note-detail__ai-btn--improve"
            onClick={handleImprove}
            disabled={isImproving || isSummarizing || isExtracting || isSuggestingTasks}
            title="Improve clarity, structure, and grammar with AI"
          >
            {isImproving ? (
              <Spinner size="sm" />
            ) : (
              <Sparkles size={16} aria-hidden="true" className="note-detail__ai-icon" />
            )}
            <span>{isImproving ? "Reviewing..." : "Improve with AI"}</span>
          </Button>
          <Button
            variant={isChatOpen ? "primary" : "secondary"}
            className="note-detail__ai-btn note-detail__ai-btn--ask"
            onClick={() => setIsChatOpen((prev) => !prev)}
            title="Ask questions about this note with AI"
          >
            <MessageSquare size={16} aria-hidden="true" className="note-detail__ai-icon" />
            <span>Ask AI</span>
          </Button>
          <Button variant="secondary" onClick={() => setIsEditOpen(true)}>
            <Pencil size={16} aria-hidden="true" />
            Edit
          </Button>
          <Button variant="danger" onClick={() => setIsDeleteOpen(true)}>
            <Trash2 size={16} aria-hidden="true" />
            Delete
          </Button>
        </div>
      }
    >
      <Link to="/notes" className="note-detail__back">
        <ArrowLeft size={14} aria-hidden="true" />
        Back to Notes
      </Link>

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
        onTasksCreated={() => {
          loadNote();
        }}
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

      <Card className="note-detail__card">
        <div className="note-detail__meta">
          <div className="note-detail__associations">
            {hasProject && (
              <Link
                to={`/projects/${note.project_id}`}
                className="note-detail__badge-link"
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
                className="note-detail__badge-link"
              >
                <Badge variant="neutral" className="note-detail__task-badge">
                  <CheckSquare size={13} aria-hidden="true" />
                  <span>{note.task_title || `Task #${note.task_id}`}</span>
                </Badge>
              </Link>
            )}

            {!hasProject && !hasTask && (
              <span className="note-detail__general-badge">General Note</span>
            )}
          </div>

          <div className="note-detail__timestamps">
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

        <div className="note-detail__body">
          <RichTextViewer
            content={note.content}
            onCheckboxToggle={handleCheckboxToggle}
            emptyMessage="This note does not have any content. Click Edit to add details."
          />
        </div>
      </Card>

      {/* Edit Note Modal */}
      <Modal
        open={isEditOpen}
        onClose={() => {
          setIsEditOpen(false);
          setFormError("");
        }}
        title="Edit Note"
      >
        <NoteForm
          initialValues={note}
          submitLabel="Save Changes"
          isSubmitting={isSaving}
          apiError={formError}
          onSubmit={handleUpdate}
          onCancel={() => {
            setIsEditOpen(false);
            setFormError("");
          }}
        />
      </Modal>

      {/* Delete Note Confirmation Dialog */}
      <DeleteNoteDialog
        note={note}
        open={isDeleteOpen}
        isDeleting={isDeleting}
        apiError={deleteError}
        onConfirm={handleDelete}
        onCancel={() => {
          setIsDeleteOpen(false);
          setDeleteError("");
        }}
      />
    </PageContainer>
  );
}

export default NoteDetailPage;
