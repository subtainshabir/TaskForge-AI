import { Circle, PlayCircle, PauseCircle, CheckCircle2, XCircle } from "lucide-react";

export const TASK_STATUSES = ["todo", "in_progress", "blocked", "completed", "cancelled"];

export const TASK_STATUS_META = {
  todo: { label: "Todo", icon: Circle, badgeVariant: "neutral" },
  in_progress: { label: "In progress", icon: PlayCircle, badgeVariant: "ai" },
  blocked: { label: "Blocked", icon: PauseCircle, badgeVariant: "danger" },
  completed: { label: "Completed", icon: CheckCircle2, badgeVariant: "success" },
  cancelled: { label: "Cancelled", icon: XCircle, badgeVariant: "neutral" },
};

export const TASK_STATUS_FILTERS = [
  { value: "", label: "All" },
  { value: "todo", label: "Todo" },
  { value: "in_progress", label: "In progress" },
  { value: "blocked", label: "Blocked" },
  { value: "completed", label: "Completed" },
  { value: "cancelled", label: "Cancelled" },
];