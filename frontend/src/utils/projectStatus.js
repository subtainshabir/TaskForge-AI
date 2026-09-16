import { CircleDot, PauseCircle, CheckCircle2, Archive } from "lucide-react";

export const PROJECT_STATUSES = ["active", "on_hold", "completed", "archived"];

export const STATUS_META = {
  active: { label: "Active", icon: CircleDot, badgeVariant: "success" },
  on_hold: { label: "On hold", icon: PauseCircle, badgeVariant: "accent" },
  completed: { label: "Completed", icon: CheckCircle2, badgeVariant: "neutral" },
  archived: { label: "Archived", icon: Archive, badgeVariant: "neutral" },
};

export const STATUS_FILTERS = [
  { value: "", label: "All" },
  { value: "active", label: "Active" },
  { value: "on_hold", label: "On hold" },
  { value: "completed", label: "Completed" },
  { value: "archived", label: "Archived" },
];