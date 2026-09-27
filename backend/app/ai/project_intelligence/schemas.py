from typing import Any, List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator

InsightTypeLiteral = Literal[
    "progress", "bottleneck", "priority", "deadline", "workload", "positive"
]
InsightSeverityLiteral = Literal["info", "low", "medium", "high"]


class ProjectProgressInsight(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    type: str = "progress"
    title: str = Field(min_length=1, max_length=255)
    description: str = Field(min_length=1, max_length=1500)
    severity: str = "info"

    @field_validator("type")
    @classmethod
    def normalize_type(cls, v: str) -> str:
        raw = (v or "").strip().lower()
        if raw in ("bottleneck", "bottle_neck", "blocker", "stalled", "stuck", "obstacle"):
            return "bottleneck"
        if raw in ("priority", "high_priority", "urgent_priority", "urgent"):
            return "priority"
        if raw in ("deadline", "due_date", "overdue", "schedule", "approaching_deadline"):
            return "deadline"
        if raw in ("workload", "distribution", "allocation", "tasks", "task_distribution"):
            return "workload"
        if raw in ("positive", "achievement", "completed", "success", "milestone", "good"):
            return "positive"
        return "progress"

    @field_validator("severity")
    @classmethod
    def normalize_severity(cls, v: str) -> str:
        raw = (v or "").strip().lower()
        if raw in ("high", "critical", "urgent", "danger"):
            return "high"
        if raw in ("medium", "moderate", "warning"):
            return "medium"
        if raw in ("low", "minor"):
            return "low"
        return "info"

    @field_validator("title")
    @classmethod
    def clean_title(cls, v: str) -> str:
        cleaned = (v or "").strip()
        for bullet in ["•", "-", "*", "1.", "2.", "3.", "4.", "5."]:
            if cleaned.startswith(bullet):
                cleaned = cleaned[len(bullet) :].strip()
        return cleaned or "Project Observation"


class ProjectProgressIntelligenceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    project_summary: str = Field(min_length=1, max_length=2000)
    overall_progress: int = Field(default=0, ge=0, le=100)
    insights: List[ProjectProgressInsight] = Field(default_factory=list)

    @field_validator("overall_progress", mode="before")
    @classmethod
    def round_progress(cls, v: Any) -> int:
        if v is None:
            return 0
        try:
            val = int(round(float(v)))
            return max(0, min(100, val))
        except (ValueError, TypeError):
            return 0
