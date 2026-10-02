from typing import List, Literal, Optional
from pydantic import BaseModel, Field, field_validator


class ProjectAISource(BaseModel):
    type: Literal["task", "note", "phase", "project"] = Field(
        ...,
        description="Type of source entity: 'task', 'note', 'phase', or 'project'.",
    )
    id: int = Field(..., description="ID of the cited source entity.")
    title: str = Field(..., description="Title or name of the cited source entity.")


class ProjectAIMessage(BaseModel):
    role: str = Field(
        ...,
        description="Role in conversation: 'user' or 'assistant'.",
    )
    content: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="Message content from previous Q&A turns.",
    )

    @field_validator("role", mode="before")
    @classmethod
    def normalize_role(cls, v: Optional[str]) -> str:
        if not v:
            return "user"
        val = str(v).strip().lower()
        if val in ("assistant", "ai", "bot", "model"):
            return "assistant"
        return "user"

    @field_validator("content")
    @classmethod
    def clean_content(cls, v: str) -> str:
        s = (v or "").strip()
        if not s:
            raise ValueError("Message content cannot be empty.")
        return s[:2000]


class ProjectAIRequest(BaseModel):
    question: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="Question to ask about the project.",
    )
    conversation_history: Optional[List[ProjectAIMessage]] = Field(
        default_factory=list,
        description="Optional temporary conversation history for follow-up context.",
    )

    @field_validator("question")
    @classmethod
    def clean_question(cls, v: str) -> str:
        s = (v or "").strip()
        if not s:
            raise ValueError("Question cannot be empty.")
        if len(s) > 1000:
            raise ValueError("Question is too long (maximum 1000 characters).")
        return s


class ProjectAIResponse(BaseModel):
    answer: str = Field(
        ...,
        min_length=1,
        description="Direct answer or recommendation synthesized strictly from project context.",
    )
    sources: List[ProjectAISource] = Field(
        default_factory=list,
        description="List of project entities (tasks, notes, phases, project) supporting the answer.",
    )
