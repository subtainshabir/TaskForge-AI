from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

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
    is_blocked: bool = False
    project_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime


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