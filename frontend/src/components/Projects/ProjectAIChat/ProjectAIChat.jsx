import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import {
  Sparkles,
  Send,
  X,
  RotateCcw,
  AlertCircle,
  CheckSquare,
  StickyNote,
  LayoutList,
  Folder,
  ExternalLink,
  Bot,
  User,
  HelpCircle,
  Target,
  Info,
} from "lucide-react";
import Spinner from "../../Spinner/Spinner.jsx";
import Button from "../../Button/Button.jsx";
import { projectService } from "../../../services/projectService.js";
import { apiErrorMessage } from "../../../utils/apiErrorMessage.js";
import "./ProjectAIChat.css";

const QUICK_PROMPTS = [
  "What is currently blocking this project?",
  "What should I focus on next?",
  "How much of the project is complete?",
  "Which tasks are incomplete?",
  "What deadlines are coming up?",
  "What decisions are in project notes?",
];

function getSourceIcon(type) {
  switch (type) {
    case "task":
      return <CheckSquare size={13} aria-hidden="true" />;
    case "note":
      return <StickyNote size={13} aria-hidden="true" />;
    case "phase":
      return <LayoutList size={13} aria-hidden="true" />;
    case "project":
    default:
      return <Folder size={13} aria-hidden="true" />;
  }
}

function getSourceRoute(type, id, projectId) {
  switch (type) {
    case "task":
      return `/projects/${projectId}/tasks/${id}`;
    case "note":
      return `/notes/${id}`;
    case "phase":
      return `/projects/${projectId}/tasks`;
    case "project":
    default:
      return `/projects/${id}`;
  }
}

function renderAnswerContent(text) {
  if (!text) return null;

  // Check if answer separates Current facts and Suggested focus
  if (text.includes("Current facts:") && text.includes("Suggested focus:")) {
    const parts = text.split("Suggested focus:");
    const factsPart = parts[0].replace("Current facts:", "").trim();
    const focusPart = (parts[1] || "").trim();

    return (
      <div className="project-ai-chat__structured-answer">
        <div className="project-ai-chat__section-block project-ai-chat__section-block--facts">
          <div className="project-ai-chat__section-header">
            <Info size={14} className="project-ai-chat__section-icon" aria-hidden="true" />
            <span className="project-ai-chat__section-label">Current Facts</span>
          </div>
          <div className="project-ai-chat__section-body">
            {factsPart.split("\n\n").map((p, idx) => (
              <p key={idx}>{p}</p>
            ))}
          </div>
        </div>

        <div className="project-ai-chat__section-block project-ai-chat__section-block--focus">
          <div className="project-ai-chat__section-header">
            <Target size={14} className="project-ai-chat__section-icon" aria-hidden="true" />
            <span className="project-ai-chat__section-label">Suggested Focus</span>
          </div>
          <div className="project-ai-chat__section-body">
            {focusPart.split("\n\n").map((p, idx) => (
              <p key={idx}>{p}</p>
            ))}
          </div>
        </div>
      </div>
    );
  }

  // Standard paragraphs
  return (
    <div className="project-ai-chat__paragraphs">
      {text.split("\n\n").map((para, idx) => (
        <p key={idx}>{para}</p>
      ))}
    </div>
  );
}

function ProjectAIChat({ projectId, projectName, open = true, onClose }) {
  const [messages, setMessages] = useState([]);
  const [question, setQuestion] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");
  const [lastQuestion, setLastQuestion] = useState("");

  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  // Reset conversation if projectId changes
  useEffect(() => {
    setMessages([]);
    setQuestion("");
    setIsLoading(false);
    setError("");
    setLastQuestion("");
  }, [projectId]);

  // Scroll to bottom when messages update
  useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages, isLoading]);

  // Focus input when opened
  useEffect(() => {
    if (open && inputRef.current) {
      inputRef.current.focus();
    }
  }, [open]);

  if (!open) return null;

  async function handleSend(questionText = question) {
    const q = (questionText || "").trim();
    if (!q || isLoading) return;

    setError("");
    setLastQuestion(q);

    const userMessage = {
      id: `user-${Date.now()}`,
      role: "user",
      content: q,
      timestamp: new Date(),
    };

    const newMessages = [...messages, userMessage];
    setMessages(newMessages);
    setQuestion("");
    setIsLoading(true);

    const historyPayload = messages.map((m) => ({
      role: m.role,
      content: m.content,
    }));

    try {
      const response = await projectService.askAIAboutProject(projectId, {
        question: q,
        conversation_history: historyPayload,
      });

      const aiMessage = {
        id: `ai-${Date.now()}`,
        role: "assistant",
        content: response.answer,
        sources: response.sources || [],
        timestamp: new Date(),
      };

      setMessages([...newMessages, aiMessage]);
    } catch (err) {
      setError(
        apiErrorMessage(
          err,
          "Failed to get AI answer for this project. Please try again."
        )
      );
    } finally {
      setIsLoading(false);
    }
  }

  function handleKeyDown(e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }

  function handleReset() {
    setMessages([]);
    setQuestion("");
    setError("");
    setLastQuestion("");
    if (inputRef.current) inputRef.current.focus();
  }

  return (
    <div
      className="project-ai-chat"
      role="region"
      aria-label="Project AI Assistant"
    >
      <div className="project-ai-chat__header">
        <div className="project-ai-chat__title-group">
          <div className="project-ai-chat__avatar-badge">
            <Sparkles size={16} aria-hidden="true" />
          </div>
          <div>
            <h3 className="project-ai-chat__title">Project AI</h3>
            <p className="project-ai-chat__subtitle">
              Ask anything about <strong>{projectName || "this project"}</strong>. Answers are derived strictly from its tasks, phases, and notes.
            </p>
          </div>
        </div>

        <div className="project-ai-chat__header-actions">
          {messages.length > 0 && (
            <button
              type="button"
              className="project-ai-chat__action-btn"
              onClick={handleReset}
              title="Clear conversation"
              aria-label="Clear conversation"
              disabled={isLoading}
            >
              <RotateCcw size={14} aria-hidden="true" />
              <span>Reset</span>
            </button>
          )}
          {onClose && (
            <button
              type="button"
              className="project-ai-chat__close-btn"
              onClick={onClose}
              title="Close Project AI"
              aria-label="Close Project AI"
            >
              <X size={18} aria-hidden="true" />
            </button>
          )}
        </div>
      </div>

      <div className="project-ai-chat__body">
        {messages.length === 0 ? (
          <div className="project-ai-chat__empty-state">
            <div className="project-ai-chat__empty-icon">
              <Bot size={28} aria-hidden="true" />
            </div>
            <h4 className="project-ai-chat__empty-title">
              How can I help with {projectName || "this project"}?
            </h4>
            <p className="project-ai-chat__empty-desc">
              Ask about current progress, blocked tasks, upcoming deadlines, phase status, or recommendations on what to prioritize next.
            </p>

            <div className="project-ai-chat__quick-prompts">
              <span className="project-ai-chat__prompts-label">
                <HelpCircle size={13} aria-hidden="true" /> Suggested questions:
              </span>
              <div className="project-ai-chat__chips">
                {QUICK_PROMPTS.map((promptText) => (
                  <button
                    key={promptText}
                    type="button"
                    className="project-ai-chat__chip"
                    onClick={() => {
                      setQuestion(promptText);
                      handleSend(promptText);
                    }}
                    disabled={isLoading}
                  >
                    {promptText}
                  </button>
                ))}
              </div>
            </div>
          </div>
        ) : (
          <div className="project-ai-chat__messages-list">
            {messages.map((msg) => (
              <div
                key={msg.id}
                className={`project-ai-chat__message project-ai-chat__message--${msg.role}`}
              >
                <div className="project-ai-chat__msg-avatar">
                  {msg.role === "user" ? (
                    <User size={14} aria-hidden="true" />
                  ) : (
                    <Bot size={14} aria-hidden="true" />
                  )}
                </div>

                <div className="project-ai-chat__msg-content">
                  <div className="project-ai-chat__msg-meta">
                    <span className="project-ai-chat__msg-author">
                      {msg.role === "user" ? "You" : "Project AI"}
                    </span>
                  </div>

                  <div className="project-ai-chat__msg-bubble">
                    {msg.role === "assistant"
                      ? renderAnswerContent(msg.content)
                      : <p>{msg.content}</p>}
                  </div>

                  {msg.sources && msg.sources.length > 0 && (
                    <div className="project-ai-chat__sources-box">
                      <span className="project-ai-chat__sources-label">Sources:</span>
                      <div className="project-ai-chat__sources-list">
                        {msg.sources.map((s, idx) => (
                          <Link
                            key={`${s.type}-${s.id}-${idx}`}
                            to={getSourceRoute(s.type, s.id, projectId)}
                            className="project-ai-chat__source-chip"
                            title={`Open ${s.type}: ${s.title}`}
                          >
                            <span className="project-ai-chat__source-type-icon">
                              {getSourceIcon(s.type)}
                            </span>
                            <span className="project-ai-chat__source-chip-title">
                              {s.title}
                            </span>
                            <ExternalLink size={11} aria-hidden="true" />
                          </Link>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            ))}

            {isLoading && (
              <div className="project-ai-chat__message project-ai-chat__message--assistant">
                <div className="project-ai-chat__msg-avatar">
                  <Bot size={14} aria-hidden="true" />
                </div>
                <div className="project-ai-chat__msg-content">
                  <div className="project-ai-chat__loading-bubble">
                    <Spinner size="xs" />
                    <span>Analyzing project...</span>
                  </div>
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>
        )}
      </div>

      {error && !isLoading && (
        <div className="project-ai-chat__error" role="alert">
          <AlertCircle size={15} aria-hidden="true" />
          <span>{error}</span>
          {lastQuestion && (
            <button
              type="button"
              className="project-ai-chat__retry-btn"
              onClick={() => handleSend(lastQuestion)}
            >
              Retry
            </button>
          )}
        </div>
      )}

      <div className="project-ai-chat__footer">
        <div className="project-ai-chat__input-bar">
          <input
            ref={inputRef}
            type="text"
            className="project-ai-chat__input"
            placeholder="Ask a question about this project..."
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={isLoading}
            aria-label="Ask Project AI a question"
          />

          <Button
            variant="primary"
            className="project-ai-chat__send-btn"
            onClick={() => handleSend()}
            disabled={!question.trim() || isLoading}
            aria-label="Send question"
          >
            {isLoading ? <Spinner size="xs" /> : <Send size={15} aria-hidden="true" />}
          </Button>
        </div>
      </div>
    </div>
  );
}

export default ProjectAIChat;
