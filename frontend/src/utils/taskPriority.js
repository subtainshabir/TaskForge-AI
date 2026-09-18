import { ArrowDown, Minus, ArrowUp, Flame } from "lucide-react";

export const TASK_PRIORITIES = ["low", "medium", "high", "urgent"];

export const TASK_PRIORITY_META = {
  low: { label: "Low", icon: ArrowDown, badgeVariant: "neutral" },
  medium: { label: "Medium", icon: Minus, badgeVariant: "accent" },
  high: { label: "High", icon: ArrowUp, badgeVariant: "accent" },
  urgent: { label: "Urgent", icon: Flame, badgeVariant: "danger" },
};