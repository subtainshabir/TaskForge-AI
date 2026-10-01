from typing import List, Optional
from pydantic import BaseModel, Field, field_validator


class TaskSuggestion(BaseModel):
    title: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Actionable task title derived strictly from the note.",
    )
    description: Optional[str] = Field(
        None,
        max_length=5000,
        description="Concise description of the task based on the note.",
    )
    priority: Optional[str] = Field(
        "medium",
        description="Priority ('low', 'medium', 'high', 'urgent') if stated, otherwise default ('medium').",
    )
    due_date: Optional[str] = Field(
        None,
        description="ISO formatted date (YYYY-MM-DD) if explicitly mentioned in the note; otherwise null.",
    )
    reason: Optional[str] = Field(
        None,
        description="Why this task was suggested based on the note content.",
    )
    confidence: Optional[float] = Field(
        0.9,
        ge=0.0,
        le=1.0,
        description="Confidence score between 0.0 and 1.0.",
    )
    is_duplicate: bool = Field(
        False,
        description="Indicates whether this suggestion matches an existing task.",
    )
    duplicate_task_title: Optional[str] = Field(
        None,
        description="Title of the existing task that this suggestion matches.",
    )

    @field_validator("priority", mode="before")
    @classmethod
    def normalize_priority(cls, v: Optional[str]) -> str:
        if not v:
            return "medium"
        val = str(v).strip().lower()
        if val in ("low", "medium", "high", "urgent"):
            return val
        if val in ("normal", "standard", "default"):
            return "medium"
        if val in ("critical", "blocker"):
            return "urgent"
        return "medium"

    @field_validator("title")
    @classmethod
    def clean_title(cls, v: str) -> str:
        s = v.strip()
        if not s:
            raise ValueError("Task title cannot be empty")
        return s[:255]


class TaskSuggestionResponse(BaseModel):
    suggestions: List[TaskSuggestion] = Field(
        default_factory=list,
        description="Actionable task suggestions derived from the note.",
    )
    project_id: Optional[int] = Field(
        None,
        description="Associated project ID if the note belongs to a project.",
    )
    project_name: Optional[str] = Field(
        None,
        description="Associated project name if the note belongs to a project.",
    )
