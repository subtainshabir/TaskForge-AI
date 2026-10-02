import DOMPurifyModule from "dompurify";

let DOMPurifyInstance = null;

function getDOMPurify() {
  if (DOMPurifyInstance) return DOMPurifyInstance;

  const win = typeof window !== "undefined" ? window : typeof globalThis !== "undefined" ? globalThis.window : null;
  if (win) {
    DOMPurifyInstance =
      typeof DOMPurifyModule.sanitize === "function"
        ? DOMPurifyModule
        : DOMPurifyModule(win);

    if (DOMPurifyInstance && typeof DOMPurifyInstance.addHook === "function") {
      DOMPurifyInstance.addHook("afterSanitizeAttributes", (node) => {
        if (node.tagName === "A") {
          node.setAttribute("target", "_blank");
          node.setAttribute("rel", "noopener noreferrer");

          const href = node.getAttribute("href") || "";
          // Disallow javascript:, vbscript:, or data: URIs
          if (/^\s*(javascript|vbscript|data):/i.test(href)) {
            node.removeAttribute("href");
          }
        }

        // Ensure checkbox inputs only allow checkbox type
        if (node.tagName === "INPUT") {
          if (node.getAttribute("type") !== "checkbox") {
            node.setAttribute("type", "checkbox");
          }
        }
      });
    }
  }

  return DOMPurifyInstance;
}

// Configure DOMPurify options for safe productivity notes
const SANITIZE_CONFIG = {
  ALLOWED_TAGS: [
    "h1",
    "h2",
    "h3",
    "h4",
    "p",
    "b",
    "strong",
    "i",
    "em",
    "u",
    "s",
    "strike",
    "ul",
    "ol",
    "li",
    "blockquote",
    "pre",
    "code",
    "hr",
    "br",
    "a",
    "span",
    "div",
    "input",
  ],
  ALLOWED_ATTR: [
    "href",
    "target",
    "rel",
    "class",
    "type",
    "checked",
    "data-checked",
    "data-item-id",
    "aria-label",
  ],
  ALLOWED_URI_REGEXP: /^(?:(?:(?:f|ht)tps?|mailto):|[^a-z]|[a-z+.\-]+(?:[^a-z+.\-:]|$))/i,
  FORCE_BODY: false,
};

/**
 * Sanitize HTML content for safe rendering.
 * @param {string} dirtyHtml
 * @returns {string} Clean, safe HTML string.
 */
export function sanitizeNoteHtml(dirtyHtml) {
  if (!dirtyHtml || typeof dirtyHtml !== "string") return "";
  const purify = getDOMPurify();
  if (purify && typeof purify.sanitize === "function") {
    return purify.sanitize(dirtyHtml, SANITIZE_CONFIG);
  }
  return escapeHtml(dirtyHtml);
}

/**
 * Check if a string contains HTML markup tags.
 * @param {string} content
 * @returns {boolean}
 */
export function isHtmlContent(content) {
  if (!content || typeof content !== "string") return false;
  return /<[a-z][\s\S]*>/i.test(content);
}

/**
 * Convert plain text content to basic HTML for editor compatibility,
 * preserving existing paragraphs and linebreaks.
 * @param {string} content
 * @returns {string}
 */
export function formatContentForEditor(content) {
  if (!content) return "";
  if (isHtmlContent(content)) {
    return sanitizeNoteHtml(content);
  }

  // Pre-process markdown code blocks if present
  let text = content;
  text = text.replace(/```([\s\S]*?)```/g, (_, code) => {
    return `<pre class="note-code-block"><code>${escapeHtml(code.trim())}</code></pre>`;
  });

  const rawBlocks = text.split(/\r?\n\r?\n/);
  const htmlBlocks = [];

  for (let block of rawBlocks) {
    block = block.trim();
    if (!block) continue;

    if (block.startsWith('<pre class="note-code-block">')) {
      htmlBlocks.push(block);
      continue;
    }

    if (block.startsWith("### ")) {
      htmlBlocks.push(`<h3>${escapeHtml(block.slice(4).trim())}</h3>`);
      continue;
    }
    if (block.startsWith("## ")) {
      htmlBlocks.push(`<h2>${escapeHtml(block.slice(3).trim())}</h2>`);
      continue;
    }
    if (block.startsWith("# ")) {
      htmlBlocks.push(`<h1>${escapeHtml(block.slice(2).trim())}</h1>`);
      continue;
    }

    if (/^[-*]\s+\[[\sxX]?\]/m.test(block)) {
      const lines = block.split(/\r?\n/);
      const items = lines.map((line) => {
        const checked = /^[-*]\s+\[[xX]\]/.test(line.trim());
        const itemText = line.trim().replace(/^[-*]\s+\[[\sxX]?\]\s*/, "");
        return `<li class="note-checklist-item" data-checked="${checked ? "true" : "false"}"><input type="checkbox"${checked ? " checked" : ""}/> ${escapeHtml(itemText)}</li>`;
      });
      htmlBlocks.push(`<ul class="note-checklist">${items.join("")}</ul>`);
      continue;
    }

    if (/^[-*]\s+/m.test(block)) {
      const lines = block.split(/\r?\n/);
      const items = lines.map((line) => {
        const itemText = line.trim().replace(/^[-*]\s+/, "");
        return `<li>${escapeHtml(itemText)}</li>`;
      });
      htmlBlocks.push(`<ul>${items.join("")}</ul>`);
      continue;
    }

    if (block.startsWith(">")) {
      const quoteText = block.replace(/^>\s*/gm, "");
      htmlBlocks.push(`<blockquote>${escapeHtml(quoteText)}</blockquote>`);
      continue;
    }

    htmlBlocks.push(`<p>${escapeHtml(block).replace(/\r?\n/g, "<br />")}</p>`);
  }

  const combined = htmlBlocks.join("");
  return sanitizeNoteHtml(combined);
}

/**
 * Extract a clean plain-text preview from HTML or plain-text content.
 * Strips all HTML tags and collapses whitespace.
 * @param {string} content
 * @param {number} maxLength
 * @returns {string}
 */
export function extractTextPreview(content, maxLength = 180) {
  if (!content || typeof content !== "string") return "";

  let text = content;
  if (isHtmlContent(content)) {
    // Replace checklist checkboxes with unicode indicator for preview
    text = text.replace(/<li[^>]*data-checked="true"[^>]*>/gi, "☑ ");
    text = text.replace(/<li[^>]*data-checked="false"[^>]*>/gi, "☐ ");
    text = text.replace(/<input[^>]*type="checkbox"[^>]*checked[^>]*>/gi, "☑ ");
    text = text.replace(/<input[^>]*type="checkbox"[^>]*>/gi, "☐ ");

    // Replace break tags and block tags with a space
    text = text
      .replace(/<br\s*\/?>/gi, " ")
      .replace(/<\/(p|div|h[1-6]|li|blockquote|pre)>/gi, " ")
      .replace(/<[^>]+>/g, "");
  }

  // Decode common HTML entities
  text = text
    .replace(/&nbsp;/g, " ")
    .replace(/&amp;/g, "&")
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/&quot;/g, '"')
    .replace(/&#39;/g, "'");

  // Collapse multiple whitespaces
  text = text.replace(/\s+/g, " ").trim();

  if (text.length <= maxLength) return text;
  return `${text.slice(0, maxLength).trim()}...`;
}

function escapeHtml(str) {
  return str
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}
