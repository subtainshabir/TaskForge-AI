import { useMemo, useRef } from "react";
import { formatContentForEditor, isHtmlContent, sanitizeNoteHtml } from "../../../utils/sanitizeHtml.js";
import "./RichTextViewer.css";

function RichTextViewer({
  content = "",
  className = "",
  onCheckboxToggle,
  emptyMessage = "No content provided in this note.",
}) {
  const containerRef = useRef(null);

  // Compute safe HTML string, with automatic plain text conversion
  const safeHtml = useMemo(() => {
    if (!content || !content.trim()) return "";
    if (isHtmlContent(content)) {
      return sanitizeNoteHtml(content);
    }
    return formatContentForEditor(content);
  }, [content]);

  // Handle clicking checkbox items in rendered view
  function handleClick(event) {
    if (event.target && event.target.type === "checkbox") {
      const checkbox = event.target;
      const li = checkbox.closest(".note-checklist-item");
      if (li && containerRef.current) {
        const isChecked = checkbox.checked;
        li.setAttribute("data-checked", isChecked ? "true" : "false");
        if (isChecked) {
          checkbox.setAttribute("checked", "checked");
        } else {
          checkbox.removeAttribute("checked");
        }

        if (onCheckboxToggle) {
          const updatedHtml = sanitizeNoteHtml(containerRef.current.innerHTML);
          onCheckboxToggle(updatedHtml);
        }
      }
    }
  }

  if (!safeHtml) {
    return <p className="rich-viewer__empty">{emptyMessage}</p>;
  }

  return (
    <div
      ref={containerRef}
      className={`rich-note-content ${className}`.trim()}
      dangerouslySetInnerHTML={{ __html: safeHtml }}
      onClick={handleClick}
    />
  );
}

export default RichTextViewer;
