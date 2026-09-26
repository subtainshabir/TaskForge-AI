from typing import List, Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator

InsightTypeLiteral = Literal["progress", "bottleneck", "stalled", "deadline", "positive"]
InsightSeverityLiteral = Literal["info", "low", "medium", "high"]


class ProgressInsightItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    type: str = "progress"
    title: str = Field(min_length=1, max_length=255)
    description: str = Field(min_length=1, max_length=1500)
    severity: str = "info"

    @field_validator("type")
    @classmethod
    def normalize_type(cls, v: str) -> str:
        raw = (v or "").strip().lower()
        if raw in ("bottleneck", "bottle_neck", "blocker", "obstacle"):
            return "bottleneck"
        if raw in ("stalled", "stuck", "inactive", "idle"):
            return "stalled"
        if raw in ("deadline", "due_date", "schedule", "urgent"):
            return "deadline"
        if raw in ("positive", "achievement", "success", "milestone", "good"):
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
        cleaned = v.strip()
        for bullet in ["•", "-", "*", "1.", "2.", "3.", "4.", "5."]:
            if cleaned.startswith(bullet):
                cleaned = cleaned[len(bullet) :].strip()
        return cleaned or "Progress Observation"


class ProgressInsightsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    summary: str = Field(min_length=1, max_length=2000)
    insights: List[ProgressInsightItem] = Field(default_factory=list)
