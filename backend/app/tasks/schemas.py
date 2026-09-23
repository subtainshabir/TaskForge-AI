from datetime import datetime
from typing import Any, Dict, Literal, Optional

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator, model_validator

TaskStatusLiteral = Literal["todo", "in_progress", "blocked", "completed", "cancelled"]
TaskPriorityLiteral = Literal["low", "medium", "high", "urgent"]


class TaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: Optional[str] = Field(default=None, max_length=5000)
    status: TaskStatusLiteral = "todo"
    priority: TaskPriorityLiteral = "medium"
    deadline: Optional[datetime] = None

    @field_validator("title")
    @classmethod
    def strip_title(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Title cannot be empty")
        return stripped


class TaskUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=255)
    description: Optional[str] = Field(default=None, max_length=5000)
    status: Optional[TaskStatusLiteral] = None
    priority: Optional[TaskPriorityLiteral] = None
    deadline: Optional[datetime] = None

    @field_validator("title")
    @classmethod
    def strip_title(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        stripped = value.strip()
        if not stripped:
            raise ValueError("Title cannot be empty")
        return stripped


class TaskResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    title: str
    description: Optional[str]
    status: TaskStatusLiteral
    priority: TaskPriorityLiteral
    deadline: Optional[datetime]
    progress: int = 0
    is_blocked: bool = False
    project_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class PhaseCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: Optional[str] = Field(default=None, max_length=2000)
    order_index: Optional[int] = None
    order: Optional[int] = None
    status: Optional[TaskStatusLiteral] = "todo"

    @field_validator("title")
    @classmethod
    def strip_title(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Title cannot be empty")
        return stripped


class PhaseUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=255)
    description: Optional[str] = Field(default=None, max_length=2000)
    order_index: Optional[int] = None
    order: Optional[int] = None
    status: Optional[TaskStatusLiteral] = None
    progress: Optional[int] = None

    @field_validator("title")
    @classmethod
    def strip_title(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        stripped = value.strip()
        if not stripped:
            raise ValueError("Title cannot be empty")
        return stripped


class PhaseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    task_id: int
    title: str
    description: Optional[str] = None
    order_index: int
    order: Optional[int] = None
    status: TaskStatusLiteral
    progress: int = 0
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    @model_validator(mode="after")
    def populate_order(self):
        if self.order is None:
            self.order = self.order_index
        return self


class PhasesGenerateRequest(BaseModel):
    replace_existing: bool = False


class TaskDependencyCreate(BaseModel):
    depends_on_task_id: int


class TaskSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    status: TaskStatusLiteral


class TaskDependencyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    task_id: int
    depends_on_task_id: int
    dependency_task: TaskSummary
    created_at: datetime


class TaskActivityResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int
    task_id: int
    user_id: int
    activity_type: str
    description: str
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        alias="metadata",
        validation_alias=AliasChoices("activity_metadata", "metadata"),
    )
    created_at: datetime