import { getDueDateInfo } from "./date.js";

export const DUE_FILTERS = [
  { value: "", label: "All" },
  { value: "overdue", label: "Overdue" },
  { value: "today", label: "Due Today" },
  { value: "tomorrow", label: "Due Tomorrow" },
  { value: "upcoming", label: "Upcoming" },
  { value: "none", label: "No Due Date" },
];

export const SORT_OPTIONS = [
  { value: "newest", label: "Newest" },
  { value: "oldest", label: "Oldest" },
  { value: "updated", label: "Recently Updated" },
  { value: "due_date", label: "Due Date" },
  { value: "priority", label: "Priority" },
  { value: "title", label: "Title" },
];

const SORT_DEFAULT_ORDER = {
  newest: "desc",
  oldest: "asc",
  updated: "desc",
  due_date: "asc",
  priority: "desc",
  title: "asc",
};

export const SORT_TOGGLEABLE = new Set(["updated", "due_date", "priority", "title"]);

const PRIORITY_RANK = { low: 0, medium: 1, high: 2, urgent: 3 };

export function defaultOrderFor(sortBy) {
  return SORT_DEFAULT_ORDER[sortBy] || "desc";
}

export function filterTasks(tasks, { status, priority, due }) {
  return tasks.filter((task) => {
    if (status && task.status !== status) return false;
    if (priority && task.priority !== priority) return false;
    if (due) {
      const urgency = getDueDateInfo(task.deadline, task.status).urgency;
      if (urgency !== due) return false;
    }
    return true;
  });
}

function fieldFor(sortBy) {
  if (sortBy === "newest" || sortBy === "oldest") return "created_at";
  if (sortBy === "updated") return "updated_at";
  if (sortBy === "due_date") return "deadline";
  return sortBy;
}

export function sortTasks(tasks, sortBy, order) {
  const field = fieldFor(sortBy);
  const direction = order === "asc" ? 1 : -1;

  return [...tasks].sort((a, b) => {
    if (field === "deadline") {
      if (!a.deadline && !b.deadline) return 0;
      if (!a.deadline) return 1;
      if (!b.deadline) return -1;
      return direction * (new Date(a.deadline) - new Date(b.deadline));
    }
    if (field === "priority") {
      return direction * (PRIORITY_RANK[a.priority] - PRIORITY_RANK[b.priority]);
    }
    if (field === "title") {
      return direction * a.title.localeCompare(b.title, undefined, { sensitivity: "base" });
    }
    return direction * (new Date(a[field]) - new Date(b[field]));
  });
}