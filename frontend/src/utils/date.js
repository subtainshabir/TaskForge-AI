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