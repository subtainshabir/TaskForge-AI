import re
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator
from app.tasks.schemas import TaskPriorityLiteral


class TaskSuggestionItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    title: str = Field(min_length=1, max_length=255, description="Actionable title for the suggested task")
    description: Optional[str] = Field(default=None, max_length=5000, description="Detailed description of the suggested work")
    reason: Optional[str] = Field(default=None, max_length=1000, description="Reason why this task is recommended based on context")
    priority: TaskPriorityLiteral = Field(default="medium", description="Suggested priority: low, medium, high, urgent")
    phase_title: Optional[str] = Field(default=None, max_length=255, description="Optional associated phase name")

    @field_validator("title", mode="before")
    @classmethod
    def clean_title(cls, v: object) -> str:
        if v is None:
            raise ValueError("Task suggestion title cannot be empty")
        s = str(v).strip()
        # Remove leading list markers like "1. ", "1) ", "- ", "* "
        s = re.sub(r"^\d+[\.\)]\s*", "", s)
        s = re.sub(r"^[-*•]\s*", "", s)
        s = s.strip()
        if not s:
            raise ValueError("Task suggestion title cannot be empty")
        return s[:255]

    @field_validator("priority", mode="before")
    @classmethod
    def clean_priority(cls, v: object) -> str:
        if v is None:
            return "medium"
        s = str(v).strip().lower()
        if s not in ("low", "medium", "high", "urgent"):
            return "medium"
        return s

    @field_validator("description", "reason", "phase_title", mode="before")
    @classmethod
    def clean_optional_strings(cls, v: object) -> Optional[str]:
        if v is None:
            return None
        s = str(v).strip()
        return s if s else None


class TaskSuggestionsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    suggestions: List[TaskSuggestionItem] = Field(default_factory=list, description="List of suggested tasks")


class ApplyTaskSuggestionsRequest(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    suggestions: List[TaskSuggestionItem] = Field(min_length=1, description="List of user-approved task suggestions to create")
