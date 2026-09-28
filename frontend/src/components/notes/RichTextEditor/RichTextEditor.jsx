import { useEffect, useRef, useState } from "react";
import {
  Bold,
  Italic,
  Underline,
  Heading1,
  Heading2,
  Heading3,
  List,
  ListOrdered,
  ListTodo,
  Quote,
  Code,
  Link as LinkIcon,
  Unlink,
  Minus,
  RemoveFormatting,
} from "lucide-react";
import { formatContentForEditor, sanitizeNoteHtml } from "../../../utils/sanitizeHtml.js";
import "./RichTextEditor.css";

function RichTextEditor({
  value = "",
  onChange,
  placeholder = "Write your note here...",
  minHeight = "220px",
  disabled = false,
}) {
  const editorRef = useRef(null);
  const isInternalUpdate = useRef(false);
  const [activeFormats, setActiveFormats] = useState({
    bold: false,
    italic: false,
    underline: false,
    heading1: false,
    heading2: false,
    heading3: false,
    bulletList: false,
    orderedList: false,
    blockquote: false,
    code: false,
  });

  const [linkModalOpen, setLinkModalOpen] = useState(false);
  const [linkUrl, setLinkUrl] = useState("");
  const [linkText, setLinkText] = useState("");
  const [linkError, setLinkError] = useState("");
  const savedSelection = useRef(null);

  // Initialize or update editor innerHTML when external `value` changes
  useEffect(() => {
    if (!editorRef.current) return;
    if (isInternalUpdate.current) {
      isInternalUpdate.current = false;
      return;
    }

    const formatted = formatContentForEditor(value);
    if (editorRef.current.innerHTML !== formatted) {
      editorRef.current.innerHTML = formatted;
    }
  }, [value]);

  // Update active formatting states based on cursor selection
  function updateActiveFormats() {
    if (!editorRef.current || !document.getSelection()) return;
    try {
      const selection = window.getSelection();
      if (!selection || selection.rangeCount === 0) return;

      const parentNode = selection.anchorNode
        ? selection.anchorNode.nodeType === 3
          ? selection.anchorNode.parentNode
          : selection.anchorNode
        : null;

      let inH1 = false;
      let inH2 = false;
      let inH3 = false;
      let inBlockquote = false;
      let inCode = false;

      let cur = parentNode;
      while (cur && cur !== editorRef.current) {
        const tag = cur.tagName ? cur.tagName.toLowerCase() : "";
        if (tag === "h1") inH1 = true;
        if (tag === "h2") inH2 = true;
        if (tag === "h3") inH3 = true;
        if (tag === "blockquote") inBlockquote = true;
        if (tag === "pre" || tag === "code") inCode = true;
        cur = cur.parentNode;
      }

      setActiveFormats({
        bold: document.queryCommandState("bold"),
        italic: document.queryCommandState("italic"),
        underline: document.queryCommandState("underline"),
        heading1: inH1,
        heading2: inH2,
        heading3: inH3,
        bulletList: document.queryCommandState("insertUnorderedList"),
        orderedList: document.queryCommandState("insertOrderedList"),
        blockquote: inBlockquote,
        code: inCode,
      });
    } catch {
      // Ignore queryCommandState errors in edge cases
    }
  }

  function handleEditorInput() {
    if (!editorRef.current) return;
    isInternalUpdate.current = true;
    const rawHtml = editorRef.current.innerHTML;

    // If editor has only empty tags like <p><br></p>, treat as empty
    const isEmpty =
      !rawHtml ||
      rawHtml === "<p><br></p>" ||
      rawHtml === "<p></p>" ||
      rawHtml === "<br>" ||
      rawHtml.trim() === "";

    const cleanHtml = isEmpty ? "" : sanitizeNoteHtml(rawHtml);
    if (onChange) {
      onChange(cleanHtml);
    }
    updateActiveFormats();
  }

  // Execute standard formatting commands
  function execCmd(command, value = null) {
    if (disabled || !editorRef.current) return;
    editorRef.current.focus();
    document.execCommand(command, false, value);
    handleEditorInput();
  }

  // Toggle Headings
  function toggleHeading(level) {
    if (disabled || !editorRef.current) return;
    editorRef.current.focus();
    const currentTag = activeFormats[`heading${level}`];
    if (currentTag) {
      document.execCommand("formatBlock", false, "<p>");
    } else {
      document.execCommand("formatBlock", false, `<h${level}>`);
    }
    handleEditorInput();
  }

  // Toggle Blockquote
  function toggleBlockquote() {
    if (disabled || !editorRef.current) return;
    editorRef.current.focus();
    if (activeFormats.blockquote) {
      document.execCommand("formatBlock", false, "<p>");
    } else {
      document.execCommand("formatBlock", false, "<blockquote>");
    }
    handleEditorInput();
  }

  // Toggle Code Block
  function toggleCodeBlock() {
    if (disabled || !editorRef.current) return;
    editorRef.current.focus();
    const selection = window.getSelection();
    if (!selection || selection.rangeCount === 0) return;

    if (activeFormats.code) {
      document.execCommand("formatBlock", false, "<p>");
    } else {
      const selectedText = selection.toString();
      const codeHtml = `<pre class="note-code-block"><code>${
        selectedText ? escapeHtml(selectedText) : "<br>"
      }</code></pre>`;
      document.execCommand("insertHTML", false, codeHtml);
    }
    handleEditorInput();
  }

  // Insert Checklist Item
  function insertChecklist() {
    if (disabled || !editorRef.current) return;
    editorRef.current.focus();

    const selection = window.getSelection();
    const selectedText = selection ? selection.toString() : "";
    const itemText = selectedText || "New checklist item";

    const checklistHtml = `<ul class="note-checklist"><li class="note-checklist-item" data-checked="false"><input type="checkbox" /> ${itemText}</li></ul><p><br></p>`;
    document.execCommand("insertHTML", false, checklistHtml);
    handleEditorInput();
  }

  // Handle clicking on checkboxes inside the editor
  function handleEditorClick(e) {
    if (e.target && e.target.type === "checkbox") {
      const li = e.target.closest(".note-checklist-item");
      if (li) {
        const isChecked = e.target.checked;
        li.setAttribute("data-checked", isChecked ? "true" : "false");
        if (isChecked) {
          e.target.setAttribute("checked", "checked");
        } else {
          e.target.removeAttribute("checked");
        }
        handleEditorInput();
      }
    }
    updateActiveFormats();
  }

  // Open Link Dialog
  function openLinkDialog() {
    if (disabled || !editorRef.current) return;
    const selection = window.getSelection();
    let text = "";
    if (selection && selection.rangeCount > 0) {
      savedSelection.current = selection.getRangeAt(0).cloneRange();
      text = selection.toString();
    } else {
      savedSelection.current = null;
    }

    setLinkText(text);
    setLinkUrl("");
    setLinkError("");
    setLinkModalOpen(true);
  }

  // Apply Link from Dialog
  function applyLink() {
    const trimmedUrl = linkUrl.trim();
    if (!trimmedUrl) {
      setLinkError("Please enter a valid URL.");
      return;
    }

    // Validate safe URL
    let safeUrl = trimmedUrl;
    if (
      !/^https?:\/\//i.test(safeUrl) &&
      !/^mailto:/i.test(safeUrl) &&
      !/^ftp:\/\//i.test(safeUrl)
    ) {
      safeUrl = `https://${safeUrl}`;
    }

    if (/^\s*(javascript|data|vbscript):/i.test(safeUrl)) {
      setLinkError("Unsafe link protocol not allowed.");
      return;
    }

    setLinkModalOpen(false);
    if (!editorRef.current) return;
    editorRef.current.focus();

    // Restore selection
    if (savedSelection.current) {
      const sel = window.getSelection();
      sel.removeAllRanges();
      sel.addRange(savedSelection.current);
    }

    const displayText = linkText.trim() || trimmedUrl;
    const linkHtml = `<a href="${safeUrl}" target="_blank" rel="noopener noreferrer">${escapeHtml(
      displayText
    )}</a>`;
    document.execCommand("insertHTML", false, linkHtml);
    handleEditorInput();
  }

  // Remove Link
  function removeLink() {
    execCmd("unlink");
  }

  // Handle special keyboard events in editor
  function handleKeyDown(event) {
    // Shortcuts: Ctrl+B, Ctrl+I, Ctrl+U
    if (event.ctrlKey || event.metaKey) {
      if (event.key === "b" || event.key === "B") {
        event.preventDefault();
        execCmd("bold");
        return;
      }
      if (event.key === "i" || event.key === "I") {
        event.preventDefault();
        execCmd("italic");
        return;
      }
      if (event.key === "u" || event.key === "U") {
        event.preventDefault();
        execCmd("underline");
        return;
      }
    }

    // Inside checklist: Enter creates next checklist item
    if (event.key === "Enter" && !event.shiftKey) {
      const selection = window.getSelection();
      if (selection && selection.anchorNode) {
        const item = selection.anchorNode.parentElement?.closest?.(".note-checklist-item");
        if (item) {
          // If current item is empty, pressing Enter exits checklist
          const itemText = item.textContent?.trim() || "";
          if (!itemText) {
            event.preventDefault();
            const p = document.createElement("p");
            p.innerHTML = "<br>";
            item.closest(".note-checklist")?.after(p);
            item.remove();
            const range = document.createRange();
            range.setStart(p, 0);
            range.collapse(true);
            selection.removeAllRanges();
            selection.addRange(range);
            handleEditorInput();
            return;
          }

          event.preventDefault();
          const newItem = document.createElement("li");
          newItem.className = "note-checklist-item";
          newItem.setAttribute("data-checked", "false");
          newItem.innerHTML = '<input type="checkbox" /> &nbsp;';
          item.after(newItem);

          const range = document.createRange();
          range.setStart(newItem, 1);
          range.collapse(true);
          selection.removeAllRanges();
          selection.addRange(range);
          handleEditorInput();
          return;
        }
      }
    }

    // Tab key in code blocks adds 2 spaces instead of leaving focus
    if (event.key === "Tab") {
      const selection = window.getSelection();
      const codeBlock = selection?.anchorNode?.parentElement?.closest?.(".note-code-block");
      if (codeBlock) {
        event.preventDefault();
        document.execCommand("insertText", false, "  ");
        handleEditorInput();
      }
    }
  }

  return (
    <div className="rich-editor">
      <div className="rich-editor__toolbar" role="toolbar" aria-label="Formatting options">
        {/* Headings */}
        <div className="rich-editor__btn-group">
          <button
            type="button"
            className={`rich-editor__btn ${activeFormats.heading1 ? "rich-editor__btn--active" : ""}`}
            title="Heading 1"
            aria-label="Heading 1"
            disabled={disabled}
            onClick={() => toggleHeading(1)}
          >
            <Heading1 size={16} aria-hidden="true" />
          </button>
          <button
            type="button"
            className={`rich-editor__btn ${activeFormats.heading2 ? "rich-editor__btn--active" : ""}`}
            title="Heading 2"
            aria-label="Heading 2"
            disabled={disabled}
            onClick={() => toggleHeading(2)}
          >
            <Heading2 size={16} aria-hidden="true" />
          </button>
          <button
            type="button"
            className={`rich-editor__btn ${activeFormats.heading3 ? "rich-editor__btn--active" : ""}`}
            title="Heading 3"
            aria-label="Heading 3"
            disabled={disabled}
            onClick={() => toggleHeading(3)}
          >
            <Heading3 size={16} aria-hidden="true" />
          </button>
        </div>

        <div className="rich-editor__separator" aria-hidden="true" />

        {/* Inline styles */}
        <div className="rich-editor__btn-group">
          <button
            type="button"
            className={`rich-editor__btn ${activeFormats.bold ? "rich-editor__btn--active" : ""}`}
            title="Bold (Ctrl+B)"
            aria-label="Bold"
            disabled={disabled}
            onClick={() => execCmd("bold")}
          >
            <Bold size={15} aria-hidden="true" />
          </button>
          <button
            type="button"
            className={`rich-editor__btn ${activeFormats.italic ? "rich-editor__btn--active" : ""}`}
            title="Italic (Ctrl+I)"
            aria-label="Italic"
            disabled={disabled}
            onClick={() => execCmd("italic")}
          >
            <Italic size={15} aria-hidden="true" />
          </button>
          <button
            type="button"
            className={`rich-editor__btn ${activeFormats.underline ? "rich-editor__btn--active" : ""}`}
            title="Underline (Ctrl+U)"
            aria-label="Underline"
            disabled={disabled}
            onClick={() => execCmd("underline")}
          >
            <Underline size={15} aria-hidden="true" />
          </button>
        </div>

        <div className="rich-editor__separator" aria-hidden="true" />

        {/* Lists & Checklists */}
        <div className="rich-editor__btn-group">
          <button
            type="button"
            className={`rich-editor__btn ${activeFormats.bulletList ? "rich-editor__btn--active" : ""}`}
            title="Bullet list"
            aria-label="Bullet list"
            disabled={disabled}
            onClick={() => execCmd("insertUnorderedList")}
          >
            <List size={16} aria-hidden="true" />
          </button>
          <button
            type="button"
            className={`rich-editor__btn ${activeFormats.orderedList ? "rich-editor__btn--active" : ""}`}
            title="Numbered list"
            aria-label="Numbered list"
            disabled={disabled}
            onClick={() => execCmd("insertOrderedList")}
          >
            <ListOrdered size={16} aria-hidden="true" />
          </button>
          <button
            type="button"
            className="rich-editor__btn"
            title="Checklist / Task list"
            aria-label="Checklist"
            disabled={disabled}
            onClick={insertChecklist}
          >
            <ListTodo size={16} aria-hidden="true" />
          </button>
        </div>

        <div className="rich-editor__separator" aria-hidden="true" />

        {/* Quotes & Code */}
        <div className="rich-editor__btn-group">
          <button
            type="button"
            className={`rich-editor__btn ${activeFormats.blockquote ? "rich-editor__btn--active" : ""}`}
            title="Blockquote"
            aria-label="Blockquote"
            disabled={disabled}
            onClick={toggleBlockquote}
          >
            <Quote size={15} aria-hidden="true" />
          </button>
          <button
            type="button"
            className={`rich-editor__btn ${activeFormats.code ? "rich-editor__btn--active" : ""}`}
            title="Code block"
            aria-label="Code block"
            disabled={disabled}
            onClick={toggleCodeBlock}
          >
            <Code size={15} aria-hidden="true" />
          </button>
        </div>

        <div className="rich-editor__separator" aria-hidden="true" />

        {/* Links & Divider */}
        <div className="rich-editor__btn-group">
          <button
            type="button"
            className="rich-editor__btn"
            title="Insert link"
            aria-label="Insert link"
            disabled={disabled}
            onClick={openLinkDialog}
          >
            <LinkIcon size={15} aria-hidden="true" />
          </button>
          <button
            type="button"
            className="rich-editor__btn"
            title="Remove link"
            aria-label="Remove link"
            disabled={disabled}
            onClick={removeLink}
          >
            <Unlink size={15} aria-hidden="true" />
          </button>
          <button
            type="button"
            className="rich-editor__btn"
            title="Horizontal separator"
            aria-label="Horizontal separator"
            disabled={disabled}
            onClick={() => execCmd("insertHorizontalRule")}
          >
            <Minus size={15} aria-hidden="true" />
          </button>
          <button
            type="button"
            className="rich-editor__btn"
            title="Clear formatting"
            aria-label="Clear formatting"
            disabled={disabled}
            onClick={() => execCmd("removeFormat")}
          >
            <RemoveFormatting size={15} aria-hidden="true" />
          </button>
        </div>
      </div>

      {/* Inline Link Modal */}
      {linkModalOpen && (
        <div className="rich-editor__link-dialog" role="dialog" aria-label="Insert Link">
          <div className="rich-editor__link-dialog-title">Insert Link</div>
          <div className="rich-editor__link-fields">
            <input
              type="text"
              className="rich-editor__link-input"
              placeholder="Display text (optional)"
              value={linkText}
              onChange={(e) => setLinkText(e.target.value)}
            />
            <input
              type="url"
              className="rich-editor__link-input"
              placeholder="https://example.com"
              value={linkUrl}
              autoFocus
              onChange={(e) => {
                setLinkUrl(e.target.value);
                setLinkError("");
              }}
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  e.preventDefault();
                  applyLink();
                } else if (e.key === "Escape") {
                  setLinkModalOpen(false);
                }
              }}
            />
          </div>
          {linkError && <span className="rich-editor__link-error">{linkError}</span>}
          <div className="rich-editor__link-actions">
            <button
              type="button"
              className="rich-editor__link-btn rich-editor__link-btn--cancel"
              onClick={() => setLinkModalOpen(false)}
            >
              Cancel
            </button>
            <button
              type="button"
              className="rich-editor__link-btn rich-editor__link-btn--primary"
              onClick={applyLink}
            >
              Insert
            </button>
          </div>
        </div>
      )}

      {/* Main ContentEditable Editor Canvas */}
      <div
        ref={editorRef}
        className="rich-editor__canvas"
        contentEditable={!disabled}
        role="textbox"
        aria-multiline="true"
        aria-label="Note content"
        data-placeholder={placeholder}
        style={{ minHeight }}
        onInput={handleEditorInput}
        onClick={handleEditorClick}
        onKeyUp={updateActiveFormats}
        onMouseUp={updateActiveFormats}
        onKeyDown={handleKeyDown}
      />
    </div>
  );
}

function escapeHtml(str) {
  return str
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

export default RichTextEditor;
