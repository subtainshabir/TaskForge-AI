import { useState } from "react";
import {
  Sparkles,
  RotateCw,
  X,
  AlertCircle,
  CheckSquare,
  CheckCircle2,
  FileText,
  Calendar,
  Users,
  Code2,
  HelpCircle,
  Copy,
  Check,
} from "lucide-react";
import Spinner from "../../Spinner/Spinner.jsx";
import Button from "../../Button/Button.jsx";
import "./NoteExtractionResult.css";

function NoteExtractionResult({
  extraction,
  isLoading = false,
  error = "",
  onRegenerate,
  onClose,
}) {
  const [copiedId, setCopiedId] = useState(null);
  const [copiedAll, setCopiedAll] = useState(false);

  if (!isLoading && !error && !extraction) {
    return null;
  }

  const actionItems = extraction?.action_items || [];
  const decisions = extraction?.decisions || [];
  const importantFacts = extraction?.important_facts || [];
  const dates = extraction?.dates || [];
  const people = extraction?.people || [];
  const technicalTerms = extraction?.technical_terms || [];
  const followUps = extraction?.follow_ups || [];

  const totalItems =
    actionItems.length +
    decisions.length +
    importantFacts.length +
    dates.length +
    people.length +
    technicalTerms.length +
    followUps.length;

  const copyToClipboard = async (text, id) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopiedId(id);
      setTimeout(() => setCopiedId(null), 2000);
    } catch {
      // Fallback
    }
  };

  const copyAllExtraction = async () => {
    if (!extraction) return;
    const sections = [];

    if (actionItems.length > 0) {
      const items = actionItems.map((item) => {
        let line = `- [ ] ${item.title}`;
        if (item.priority) line += ` (Priority: ${item.priority.toUpperCase()})`;
        if (item.details) line += `\n  ${item.details}`;
        return line;
      });
      sections.push(`### Action Items\n${items.join("\n")}`);
    }

    if (decisions.length > 0) {
      sections.push(`### Decisions\n${decisions.map((d) => `- ${d}`).join("\n")}`);
    }

    if (importantFacts.length > 0) {
      sections.push(
        `### Important Facts\n${importantFacts.map((f) => `- ${f}`).join("\n")}`
      );
    }

    if (dates.length > 0) {
      const dateLines = dates.map((d) => {
        let line = `- ${d.text}`;
        if (d.date) line += ` [${d.date}]`;
        if (d.context) line += ` — ${d.context}`;
        return line;
      });
      sections.push(`### Dates & Deadlines\n${dateLines.join("\n")}`);
    }

    if (people.length > 0) {
      sections.push(
        `### People & Entities\n${people.map((p) => `- ${p}`).join("\n")}`
      );
    }

    if (technicalTerms.length > 0) {
      sections.push(`### Technical Terms\n${technicalTerms.join(", ")}`);
    }

    if (followUps.length > 0) {
      sections.push(
        `### Follow-ups\n${followUps.map((fu) => `- ${fu}`).join("\n")}`
      );
    }

    const fullMarkdown = sections.join("\n\n");
    try {
      await navigator.clipboard.writeText(fullMarkdown);
      setCopiedAll(true);
      setTimeout(() => setCopiedAll(false), 2000);
    } catch {
      // Fallback
    }
  };

  return (
    <div
      className="note-extraction-result"
      role="region"
      aria-label="AI Note Information Extraction"
    >
      <div className="note-extraction-result__header">
        <div className="note-extraction-result__title-group">
          <Sparkles
            size={16}
            className="note-extraction-result__sparkle-icon"
            aria-hidden="true"
          />
          <h3 className="note-extraction-result__title">AI Extracted Information</h3>
          <span className="note-extraction-result__badge">AI-Extracted</span>
        </div>

        <div className="note-extraction-result__header-actions">
          {extraction && totalItems > 0 && (
            <button
              type="button"
              className="note-extraction-result__action-btn"
              onClick={copyAllExtraction}
              title="Copy all extracted items as Markdown"
              aria-label="Copy all extracted items"
            >
              {copiedAll ? (
                <>
                  <Check size={13} aria-hidden="true" />
                  <span>Copied All!</span>
                </>
              ) : (
                <>
                  <Copy size={13} aria-hidden="true" />
                  <span>Copy All</span>
                </>
              )}
            </button>
          )}

          {onRegenerate && (
            <button
              type="button"
              className="note-extraction-result__action-btn"
              onClick={onRegenerate}
              disabled={isLoading}
              title="Re-extract information with AI"
              aria-label="Re-extract information"
            >
              <RotateCw
                size={13}
                className={isLoading ? "note-extraction-result__spin" : ""}
                aria-hidden="true"
              />
              <span>Re-extract</span>
            </button>
          )}

          {onClose && (
            <button
              type="button"
              className="note-extraction-result__close-btn"
              onClick={onClose}
              title="Dismiss extraction"
              aria-label="Dismiss extraction"
            >
              <X size={15} aria-hidden="true" />
            </button>
          )}
        </div>
      </div>

      {isLoading && (
        <div className="note-extraction-result__loading">
          <Spinner size="sm" label="Extracting information..." />
          <p className="note-extraction-result__loading-text">
            Analyzing note and extracting action items, decisions, facts, and dates...
          </p>
        </div>
      )}

      {error && !isLoading && (
        <div className="note-extraction-result__error" role="alert">
          <AlertCircle
            size={16}
            className="note-extraction-result__error-icon"
            aria-hidden="true"
          />
          <div className="note-extraction-result__error-body">
            <span className="note-extraction-result__error-msg">{error}</span>
            {onRegenerate && (
              <Button
                type="button"
                variant="ghost"
                size="sm"
                className="note-extraction-result__retry-btn"
                onClick={onRegenerate}
              >
                Try Again
              </Button>
            )}
          </div>
        </div>
      )}

      {!isLoading && !error && extraction && totalItems === 0 && (
        <div className="note-extraction-result__empty">
          <p>
            No structured items (action items, decisions, facts, dates, etc.) were
            found in this note.
          </p>
        </div>
      )}

      {!isLoading && !error && extraction && totalItems > 0 && (
        <div className="note-extraction-result__content">
          {/* Action Items */}
          {actionItems.length > 0 && (
            <section
              className="note-extraction-result__section"
              aria-labelledby="extraction-section-action-items"
            >
              <h4
                id="extraction-section-action-items"
                className="note-extraction-result__section-title"
              >
                <CheckSquare size={14} aria-hidden="true" />
                <span>Action Items ({actionItems.length})</span>
              </h4>
              <ul className="note-extraction-result__list">
                {actionItems.map((item, idx) => {
                  const id = `action-${idx}`;
                  const isCopied = copiedId === id;
                  return (
                    <li key={idx} className="note-extraction-result__item">
                      <div className="note-extraction-result__item-main">
                        <div className="note-extraction-result__item-title-row">
                          <span className="note-extraction-result__item-text">
                            {item.title}
                          </span>
                          {item.priority && (
                            <span
                              className={`note-extraction-result__priority-badge note-extraction-result__priority-badge--${item.priority.toLowerCase()}`}
                            >
                              {item.priority}
                            </span>
                          )}
                        </div>
                        {item.details && (
                          <span className="note-extraction-result__item-detail">
                            {item.details}
                          </span>
                        )}
                      </div>
                      <button
                        type="button"
                        className="note-extraction-result__item-copy"
                        onClick={() =>
                          copyToClipboard(
                            `${item.title}${item.details ? ` - ${item.details}` : ""}`,
                            id
                          )
                        }
                        title="Copy action item"
                        aria-label="Copy action item"
                      >
                        {isCopied ? <Check size={12} /> : <Copy size={12} />}
                      </button>
                    </li>
                  );
                })}
              </ul>
            </section>
          )}

          {/* Decisions */}
          {decisions.length > 0 && (
            <section
              className="note-extraction-result__section"
              aria-labelledby="extraction-section-decisions"
            >
              <h4
                id="extraction-section-decisions"
                className="note-extraction-result__section-title"
              >
                <CheckCircle2 size={14} aria-hidden="true" />
                <span>Decisions ({decisions.length})</span>
              </h4>
              <ul className="note-extraction-result__list">
                {decisions.map((decision, idx) => {
                  const id = `decision-${idx}`;
                  const isCopied = copiedId === id;
                  return (
                    <li key={idx} className="note-extraction-result__item">
                      <span className="note-extraction-result__item-text">
                        {decision}
                      </span>
                      <button
                        type="button"
                        className="note-extraction-result__item-copy"
                        onClick={() => copyToClipboard(decision, id)}
                        title="Copy decision"
                        aria-label="Copy decision"
                      >
                        {isCopied ? <Check size={12} /> : <Copy size={12} />}
                      </button>
                    </li>
                  );
                })}
              </ul>
            </section>
          )}

          {/* Important Facts */}
          {importantFacts.length > 0 && (
            <section
              className="note-extraction-result__section"
              aria-labelledby="extraction-section-facts"
            >
              <h4
                id="extraction-section-facts"
                className="note-extraction-result__section-title"
              >
                <FileText size={14} aria-hidden="true" />
                <span>Important Facts ({importantFacts.length})</span>
              </h4>
              <ul className="note-extraction-result__list">
                {importantFacts.map((fact, idx) => {
                  const id = `fact-${idx}`;
                  const isCopied = copiedId === id;
                  return (
                    <li key={idx} className="note-extraction-result__item">
                      <span className="note-extraction-result__item-text">
                        {fact}
                      </span>
                      <button
                        type="button"
                        className="note-extraction-result__item-copy"
                        onClick={() => copyToClipboard(fact, id)}
                        title="Copy fact"
                        aria-label="Copy fact"
                      >
                        {isCopied ? <Check size={12} /> : <Copy size={12} />}
                      </button>
                    </li>
                  );
                })}
              </ul>
            </section>
          )}

          {/* Dates & Deadlines */}
          {dates.length > 0 && (
            <section
              className="note-extraction-result__section"
              aria-labelledby="extraction-section-dates"
            >
              <h4
                id="extraction-section-dates"
                className="note-extraction-result__section-title"
              >
                <Calendar size={14} aria-hidden="true" />
                <span>Dates & Deadlines ({dates.length})</span>
              </h4>
              <ul className="note-extraction-result__list">
                {dates.map((dateItem, idx) => {
                  const id = `date-${idx}`;
                  const isCopied = copiedId === id;
                  return (
                    <li key={idx} className="note-extraction-result__item">
                      <div className="note-extraction-result__item-main">
                        <div className="note-extraction-result__item-title-row">
                          <strong className="note-extraction-result__date-text">
                            {dateItem.text}
                          </strong>
                          {dateItem.date && (
                            <span className="note-extraction-result__iso-date">
                              {dateItem.date}
                            </span>
                          )}
                        </div>
                        {dateItem.context && (
                          <span className="note-extraction-result__item-detail">
                            {dateItem.context}
                          </span>
                        )}
                      </div>
                      <button
                        type="button"
                        className="note-extraction-result__item-copy"
                        onClick={() =>
                          copyToClipboard(
                            `${dateItem.text}${dateItem.context ? ` — ${dateItem.context}` : ""}`,
                            id
                          )
                        }
                        title="Copy date"
                        aria-label="Copy date"
                      >
                        {isCopied ? <Check size={12} /> : <Copy size={12} />}
                      </button>
                    </li>
                  );
                })}
              </ul>
            </section>
          )}

          {/* People & Entities */}
          {people.length > 0 && (
            <section
              className="note-extraction-result__section"
              aria-labelledby="extraction-section-people"
            >
              <h4
                id="extraction-section-people"
                className="note-extraction-result__section-title"
              >
                <Users size={14} aria-hidden="true" />
                <span>People & Entities ({people.length})</span>
              </h4>
              <div className="note-extraction-result__tags">
                {people.map((person, idx) => (
                  <span key={idx} className="note-extraction-result__tag">
                    {person}
                  </span>
                ))}
              </div>
            </section>
          )}

          {/* Technical Terms */}
          {technicalTerms.length > 0 && (
            <section
              className="note-extraction-result__section"
              aria-labelledby="extraction-section-tech"
            >
              <h4
                id="extraction-section-tech"
                className="note-extraction-result__section-title"
              >
                <Code2 size={14} aria-hidden="true" />
                <span>Technical Terms ({technicalTerms.length})</span>
              </h4>
              <div className="note-extraction-result__tags">
                {technicalTerms.map((term, idx) => (
                  <span
                    key={idx}
                    className="note-extraction-result__tag note-extraction-result__tag--code"
                  >
                    <code>{term}</code>
                  </span>
                ))}
              </div>
            </section>
          )}

          {/* Follow-ups */}
          {followUps.length > 0 && (
            <section
              className="note-extraction-result__section"
              aria-labelledby="extraction-section-followups"
            >
              <h4
                id="extraction-section-followups"
                className="note-extraction-result__section-title"
              >
                <HelpCircle size={14} aria-hidden="true" />
                <span>Follow-ups ({followUps.length})</span>
              </h4>
              <ul className="note-extraction-result__list">
                {followUps.map((item, idx) => {
                  const id = `fu-${idx}`;
                  const isCopied = copiedId === id;
                  return (
                    <li key={idx} className="note-extraction-result__item">
                      <span className="note-extraction-result__item-text">
                        {item}
                      </span>
                      <button
                        type="button"
                        className="note-extraction-result__item-copy"
                        onClick={() => copyToClipboard(item, id)}
                        title="Copy follow-up"
                        aria-label="Copy follow-up"
                      >
                        {isCopied ? <Check size={12} /> : <Copy size={12} />}
                      </button>
                    </li>
                  );
                })}
              </ul>
            </section>
          )}
        </div>
      )}
    </div>
  );
}

export default NoteExtractionResult;
