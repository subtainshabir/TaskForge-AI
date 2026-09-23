export function formatAbsoluteDate(value) {
  if (!value) return "—";
  return new Date(value).toLocaleDateString(undefined, {
    year: "numeric",
    month: "long",
    day: "numeric",
  });
}

export function formatRelativeDate(value) {
  if (!value) return "—";
  const date = new Date(value);
  const now = new Date();
  const diffDays = Math.floor((now.setHours(0, 0, 0, 0) - new Date(date).setHours(0, 0, 0, 0)) / 86400000);

  if (diffDays === 0) return "today";
  if (diffDays === 1) return "yesterday";
  if (diffDays > 1 && diffDays < 7) return `${diffDays} days ago`;

  return date.toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" });
}

export function formatActivityTime(value) {
  if (!value) return "—";
  const date = new Date(value);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  if (diffMs < 0) return "just now";
  const diffSec = Math.floor(diffMs / 1000);
  if (diffSec < 45) return "just now";
  const diffMin = Math.floor(diffSec / 60);
  if (diffMin < 60) return diffMin === 1 ? "1 minute ago" : `${diffMin} minutes ago`;
  const diffHours = Math.floor(diffMin / 60);
  if (diffHours < 24) return diffHours === 1 ? "1 hour ago" : `${diffHours} hours ago`;
  const diffDays = Math.floor(diffHours / 24);
  if (diffDays === 1) {
    const timeStr = date.toLocaleTimeString(undefined, { hour: "numeric", minute: "2-digit" });
    return `Yesterday, ${timeStr}`;
  }
  if (diffDays < 7) return `${diffDays} days ago`;
  return date.toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
    year: date.getFullYear() !== now.getFullYear() ? "numeric" : undefined,
  });
}

export function formatDueDate(value) {
  if (!value) return null;
  const date = new Date(value);
  const startOfDay = (d) => new Date(d.getFullYear(), d.getMonth(), d.getDate());
  const diffDays = Math.round((startOfDay(date) - startOfDay(new Date())) / 86400000);

  if (diffDays === 0) return "Today";
  if (diffDays === 1) return "Tomorrow";
  if (diffDays === -1) return "Yesterday";

  return date.toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" });
}

export function isOverdue(value, status) {
  if (!value || status === "completed" || status === "cancelled") return false;
  const startOfDay = (d) => new Date(d.getFullYear(), d.getMonth(), d.getDate());
  return startOfDay(new Date(value)) < startOfDay(new Date());
}

export function toDateInputValue(value) {
  if (!value) return "";
  const date = new Date(value);
  const offset = date.getTimezoneOffset();
  return new Date(date.getTime() - offset * 60000).toISOString().slice(0, 10);
}

export const DUE_URGENCY_META = {
  overdue: { badgeVariant: "danger" },
  today: { badgeVariant: "accent" },
  tomorrow: { badgeVariant: "ai" },
  upcoming: { badgeVariant: "neutral" },
  done: { badgeVariant: "neutral" },
  none: { badgeVariant: "neutral" },
};

export function getDueDateInfo(value, status) {
  if (!value) return { label: "No due date", urgency: "none" };

  const startOfDay = (d) => new Date(d.getFullYear(), d.getMonth(), d.getDate());
  const diffDays = Math.round((startOfDay(new Date(value)) - startOfDay(new Date())) / 86400000);
  const isDone = status === "completed" || status === "cancelled";

  if (isDone) {
    return { label: `Due ${formatDueDate(value)}`, urgency: "done" };
  }
  if (diffDays < 0) {
    const overdueDays = Math.abs(diffDays);
    const label = overdueDays === 1 ? "Due yesterday" : `${overdueDays} days overdue`;
    return { label, urgency: "overdue" };
  }
  if (diffDays === 0) return { label: "Due today", urgency: "today" };
  if (diffDays === 1) return { label: "Due tomorrow", urgency: "tomorrow" };
  return { label: `Due ${formatDueDate(value)}`, urgency: "upcoming" };
}