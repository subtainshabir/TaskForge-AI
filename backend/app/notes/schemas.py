from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class NoteCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    content: Optional[str] = Field(default=None, max_length=50000)
    project_id: Optional[int] = None
    task_id: Optional[int] = None

    @field_validator("title")
    @classmethod
    def strip_title(cls, value: str) -> str:
        stripped = (value or "").strip()
        if not stripped:
            raise ValueError("Title cannot be empty")
        return stripped


class NoteUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=255)
    content: Optional[str] = Field(default=None, max_length=50000)

    @field_validator("title")
    @classmethod
    def strip_title(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        stripped = value.strip()
        if not stripped:
            raise ValueError("Title cannot be empty")
        return stripped


class NoteResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    project_id: Optional[int] = None
    task_id: Optional[int] = None
    title: str
    content: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    project_name: Optional[str] = None
    task_title: Optional[str] = None
