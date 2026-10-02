import { useEffect, useRef, useState } from "react";
import {
  MessageSquare,
  Sparkles,
  Send,
  X,
  RotateCcw,
  AlertCircle,
  User,
  Bot,
  HelpCircle,
} from "lucide-react";
import Spinner from "../../Spinner/Spinner.jsx";
import Button from "../../Button/Button.jsx";
import { noteService } from "../../../services/noteService.js";
import { apiErrorMessage } from "../../../utils/apiErrorMessage.js";
import "./NoteAIChat.css";

const QUICK_PROMPTS = [
  "What is the deadline?",
  "What is the main objective?",
  "What action items are listed?",
  "What decisions were made?",
];

function NoteAIChat({ note, open = true, onClose }) {
  const [messages, setMessages] = useState([]);
  const [question, setQuestion] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");
  const [lastQuestion, setLastQuestion] = useState("");

  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  // Reset conversation when opening a different note
  useEffect(() => {
    setMessages([]);
    setQuestion("");
    setIsLoading(false);
    setError("");
    setLastQuestion("");
  }, [note?.id]);

  // Scroll to bottom whenever messages change or loading state changes
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

  if (!open || !note) return null;

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

    // Format previous messages for conversation history
    const conversationHistory = messages.map((m) => ({
      role: m.role,
      content: m.content,
    }));

    try {
      const response = await noteService.askAIAboutNote(note.id, {
        question: q,
        conversation_history: conversationHistory,
      });

      const aiMessage = {
        id: `ai-${Date.now()}`,
        role: "assistant",
        content: response.answer,
        timestamp: new Date(),
      };

      setMessages([...newMessages, aiMessage]);
    } catch (err) {
      setError(apiErrorMessage(err, "Failed to get an answer from AI."));
    } finally {
      setIsLoading(false);
    }
  }

  function handleKeyDown(event) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      handleSend();
    }
  }

  function handleClearChat() {
    setMessages([]);
    setError("");
    setLastQuestion("");
    if (inputRef.current) {
      inputRef.current.focus();
    }
  }

  function handleRetry() {
    if (lastQuestion) {
      handleSend(lastQuestion);
    }
  }

  return (
    <section
      className="note-ai-chat"
      role="region"
      aria-label="Ask AI About This Note"
    >
      {/* Header */}
      <div className="note-ai-chat__header">
        <div className="note-ai-chat__title-group">
          <MessageSquare
            size={16}
            className="note-ai-chat__icon"
            aria-hidden="true"
          />
          <h3 className="note-ai-chat__title">Ask AI About This Note</h3>
          <span className="note-ai-chat__badge">AI Q&A</span>
        </div>

        <div className="note-ai-chat__header-actions">
          {messages.length > 0 && (
            <button
              type="button"
              className="note-ai-chat__action-btn"
              onClick={handleClearChat}
              disabled={isLoading}
              title="Clear conversation history"
              aria-label="Clear chat"
            >
              <RotateCcw size={13} aria-hidden="true" />
              <span>Clear</span>
            </button>
          )}
          {onClose && (
            <button
              type="button"
              className="note-ai-chat__close-btn"
              onClick={onClose}
              title="Close Q&A"
              aria-label="Close Q&A"
            >
              <X size={15} aria-hidden="true" />
            </button>
          )}
        </div>
      </div>

      {/* Messages Feed */}
      <div className="note-ai-chat__messages-container">
        {messages.length === 0 && !isLoading && (
          <div className="note-ai-chat__empty">
            <HelpCircle size={28} className="note-ai-chat__empty-icon" />
            <h4 className="note-ai-chat__empty-title">
              Ask anything about "{note.title}"
            </h4>
            <p className="note-ai-chat__empty-desc">
              The AI answers questions derived strictly from this note's content.
              If the information is not in the note, it will let you know.
            </p>

            {/* Quick Suggestion Chips */}
            <div className="note-ai-chat__quick-prompts">
              <span className="note-ai-chat__quick-label">Suggested questions:</span>
              <div className="note-ai-chat__quick-chips">
                {QUICK_PROMPTS.map((promptText, idx) => (
                  <button
                    key={idx}
                    type="button"
                    className="note-ai-chat__chip"
                    onClick={() => handleSend(promptText)}
                    disabled={isLoading}
                  >
                    {promptText}
                  </button>
                ))}
              </div>
            </div>
          </div>
        )}

        {messages.map((msg) => {
          const isUser = msg.role === "user";
          return (
            <div
              key={msg.id}
              className={`note-ai-chat__message ${
                isUser
                  ? "note-ai-chat__message--user"
                  : "note-ai-chat__message--ai"
              }`}
            >
              <div
                className={`note-ai-chat__avatar ${
                  isUser
                    ? "note-ai-chat__avatar--user"
                    : "note-ai-chat__avatar--ai"
                }`}
                aria-hidden="true"
              >
                {isUser ? <User size={13} /> : <Sparkles size={13} />}
              </div>

              <div className="note-ai-chat__bubble">
                <div className="note-ai-chat__bubble-header">
                  <span className="note-ai-chat__sender-name">
                    {isUser ? "You" : "TaskForge AI"}
                  </span>
                </div>
                <div className="note-ai-chat__bubble-content">
                  <p>{msg.content}</p>
                </div>
              </div>
            </div>
          );
        })}

        {/* Loading Indicator */}
        {isLoading && (
          <div className="note-ai-chat__message note-ai-chat__message--ai">
            <div
              className="note-ai-chat__avatar note-ai-chat__avatar--ai"
              aria-hidden="true"
            >
              <Sparkles size={13} />
            </div>
            <div className="note-ai-chat__bubble note-ai-chat__bubble--loading">
              <div className="note-ai-chat__loading-body">
                <Spinner size="sm" />
                <span className="note-ai-chat__loading-text">
                  AI is reading the note...
                </span>
              </div>
            </div>
          </div>
        )}

        {/* Error Banner */}
        {error && (
          <div className="note-ai-chat__error" role="alert">
            <AlertCircle size={15} className="note-ai-chat__error-icon" />
            <div className="note-ai-chat__error-text">
              <span>{error}</span>
              {lastQuestion && (
                <button
                  type="button"
                  className="note-ai-chat__retry-link"
                  onClick={handleRetry}
                  disabled={isLoading}
                >
                  Retry question
                </button>
              )}
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <form
        className="note-ai-chat__form"
        onSubmit={(e) => {
          e.preventDefault();
          handleSend();
        }}
      >
        <input
          ref={inputRef}
          type="text"
          className="note-ai-chat__input"
          placeholder="Ask a question about this note... (e.g. What is the deadline?)"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={isLoading}
          maxLength={1000}
          aria-label="Question about this note"
        />

        <Button
          type="submit"
          variant="primary"
          size="sm"
          className="note-ai-chat__submit-btn"
          disabled={!question.trim() || isLoading}
          title="Send question"
        >
          {isLoading ? (
            <Spinner size="sm" />
          ) : (
            <Send size={14} aria-hidden="true" />
          )}
          <span>Ask</span>
        </Button>
      </form>
    </section>
  );
}

export default NoteAIChat;
