import { useEffect, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  Sparkles,
  Search,
  X,
  RotateCcw,
  AlertCircle,
  FileText,
  ExternalLink,
  Bot,
  HelpCircle,
} from "lucide-react";
import Button from "../../Button/Button.jsx";
import Spinner from "../../Spinner/Spinner.jsx";
import { noteService } from "../../../services/noteService.js";
import { apiErrorMessage } from "../../../utils/apiErrorMessage.js";
import "./NoteAISearch.css";

const QUICK_PROMPTS = [
  "Which notes discuss authentication?",
  "Which notes mention PostgreSQL?",
  "What deadlines are mentioned in my notes?",
  "What are the key technical decisions?",
];

function NoteAISearch({
  open = true,
  onClose,
  onSelectNote,
}) {
  const [question, setQuestion] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [loadingStep, setLoadingStep] = useState("search"); // 'search' | 'analyze'
  const [error, setError] = useState("");
  const [lastQuestion, setLastQuestion] = useState("");
  const [result, setResult] = useState(null); // { answer: string, sources: [] }

  const inputRef = useRef(null);
  const loadingTimerRef = useRef(null);
  const navigate = useNavigate();

  // Focus input when opened
  useEffect(() => {
    if (open && inputRef.current) {
      inputRef.current.focus();
    }
  }, [open]);

  // Clean up loading timer on unmount
  useEffect(() => {
    return () => {
      if (loadingTimerRef.current) {
        clearTimeout(loadingTimerRef.current);
      }
    };
  }, []);

  if (!open) return null;

  async function handleSearch(queryText = question) {
    const q = (queryText || "").trim();
    if (!q || isLoading) return;

    setError("");
    setLastQuestion(q);
    setIsLoading(true);
    setLoadingStep("search");

    // Progressive loading state: "Searching your notes..." -> "Analyzing relevant notes..."
    if (loadingTimerRef.current) clearTimeout(loadingTimerRef.current);
    loadingTimerRef.current = setTimeout(() => {
      setLoadingStep("analyze");
    }, 700);

    try {
      const response = await noteService.searchAIAcrossNotes({ question: q });
      setResult(response);
    } catch (err) {
      setError(
        apiErrorMessage(
          err,
          "Failed to search notes. Please try asking your question again."
        )
      );
    } finally {
      if (loadingTimerRef.current) clearTimeout(loadingTimerRef.current);
      setIsLoading(false);
    }
  }

  function handleKeyDown(e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSearch();
    }
  }

  function handleReset() {
    setQuestion("");
    setResult(null);
    setError("");
    setLastQuestion("");
    if (inputRef.current) {
      inputRef.current.focus();
    }
  }

  function handleSourceClick(e, source) {
    if (onSelectNote) {
      e.preventDefault();
      onSelectNote(source.note_id);
    } else {
      navigate(`/notes/${source.note_id}`);
    }
  }

  return (
    <div
      className="note-ai-search"
      role="region"
      aria-label="Ask AI Across Notes"
    >
      <div className="note-ai-search__header">
        <div className="note-ai-search__title-group">
          <div className="note-ai-search__badge">
            <Sparkles size={16} aria-hidden="true" />
          </div>
          <div>
            <h3 className="note-ai-search__title">Ask AI Across Notes</h3>
            <p className="note-ai-search__subtitle">
              Ask questions across all your notes. Answers are synthesized using only your accessible notes.
            </p>
          </div>
        </div>

        <div className="note-ai-search__header-actions">
          {(result || question || error) && (
            <button
              type="button"
              className="note-ai-search__action-btn"
              onClick={handleReset}
              title="Reset search"
              aria-label="Reset search"
              disabled={isLoading}
            >
              <RotateCcw size={15} aria-hidden="true" />
              <span>Reset</span>
            </button>
          )}
          {onClose && (
            <button
              type="button"
              className="note-ai-search__close-btn"
              onClick={onClose}
              title="Close AI search"
              aria-label="Close AI search"
            >
              <X size={18} aria-hidden="true" />
            </button>
          )}
        </div>
      </div>

      <div className="note-ai-search__input-wrapper">
        <div className="note-ai-search__input-bar">
          <Search size={18} className="note-ai-search__input-icon" aria-hidden="true" />
          <input
            ref={inputRef}
            type="text"
            className="note-ai-search__input"
            placeholder="e.g. Which notes discuss authentication? What was the deadline?"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={isLoading}
            aria-label="Ask AI a question across your notes"
          />
          {question && !isLoading && (
            <button
              type="button"
              className="note-ai-search__clear-input"
              onClick={() => {
                setQuestion("");
                if (inputRef.current) inputRef.current.focus();
              }}
              aria-label="Clear question text"
            >
              <X size={14} aria-hidden="true" />
            </button>
          )}
          <Button
            variant="primary"
            className="note-ai-search__submit-btn"
            onClick={() => handleSearch()}
            disabled={!question.trim() || isLoading}
            aria-busy={isLoading}
          >
            {isLoading ? (
              <>
                <Spinner size="xs" />
                <span>Searching...</span>
              </>
            ) : (
              <>
                <Sparkles size={15} aria-hidden="true" />
                <span>Ask AI</span>
              </>
            )}
          </Button>
        </div>

        {!result && !isLoading && (
          <div className="note-ai-search__quick-prompts">
            <span className="note-ai-search__prompts-label">
              <HelpCircle size={13} aria-hidden="true" /> Try asking:
            </span>
            <div className="note-ai-search__chips">
              {QUICK_PROMPTS.map((promptText) => (
                <button
                  key={promptText}
                  type="button"
                  className="note-ai-search__chip"
                  onClick={() => {
                    setQuestion(promptText);
                    handleSearch(promptText);
                  }}
                  disabled={isLoading}
                >
                  {promptText}
                </button>
              ))}
            </div>
          </div>
        )}
      </div>

      {isLoading && (
        <div className="note-ai-search__loading" aria-live="polite">
          <Spinner size="sm" />
          <span className="note-ai-search__loading-text">
            {loadingStep === "search"
              ? "Searching your notes..."
              : "Analyzing relevant notes..."}
          </span>
        </div>
      )}

      {error && !isLoading && (
        <div className="note-ai-search__error" role="alert">
          <AlertCircle size={16} aria-hidden="true" className="note-ai-search__error-icon" />
          <div className="note-ai-search__error-body">
            <span>{error}</span>
            {lastQuestion && (
              <button
                type="button"
                className="note-ai-search__retry-link"
                onClick={() => handleSearch(lastQuestion)}
              >
                Retry
              </button>
            )}
          </div>
        </div>
      )}

      {result && !isLoading && (
        <div className="note-ai-search__result-area">
          <div className="note-ai-search__answer-card">
            <div className="note-ai-search__answer-header">
              <div className="note-ai-search__bot-avatar">
                <Bot size={16} aria-hidden="true" />
              </div>
              <span className="note-ai-search__answer-label">AI Answer</span>
            </div>
            <div className="note-ai-search__answer-content">
              {result.answer.split("\n\n").map((para, idx) => (
                <p key={idx}>{para}</p>
              ))}
            </div>
          </div>

          {result.sources && result.sources.length > 0 && (
            <div className="note-ai-search__sources-section">
              <div className="note-ai-search__sources-heading">
                <FileText size={15} aria-hidden="true" />
                <span>Sources</span>
                <span className="note-ai-search__sources-count">
                  {result.sources.length}
                </span>
              </div>

              <div className="note-ai-search__sources-list">
                {result.sources.map((source) => (
                  <Link
                    key={source.note_id}
                    to={`/notes/${source.note_id}`}
                    onClick={(e) => handleSourceClick(e, source)}
                    className="note-ai-search__source-item"
                    title={`Open note: ${source.title}`}
                  >
                    <div className="note-ai-search__source-icon">
                      <FileText size={14} aria-hidden="true" />
                    </div>
                    <span className="note-ai-search__source-title">
                      {source.title}
                    </span>
                    <ExternalLink
                      size={13}
                      className="note-ai-search__source-arrow"
                      aria-hidden="true"
                    />
                  </Link>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default NoteAISearch;
