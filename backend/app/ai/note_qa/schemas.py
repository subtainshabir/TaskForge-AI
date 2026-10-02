from typing import List, Optional
from pydantic import BaseModel, Field, field_validator


class NoteQAMessage(BaseModel):
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
        s = v.strip()
        if not s:
            raise ValueError("Message content cannot be empty.")
        return s[:2000]


class NoteQARequest(BaseModel):
    question: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="Question to ask about the note's content.",
    )
    conversation_history: Optional[List[NoteQAMessage]] = Field(
        default_factory=list,
        description="Optional prior exchanges in this Q&A session for follow-up context.",
    )

    @field_validator("question")
    @classmethod
    def clean_question(cls, v: str) -> str:
        s = v.strip()
        if not s:
            raise ValueError("Question cannot be empty.")
        if len(s) > 1000:
            raise ValueError("Question is too long (maximum 1000 characters).")
        return s


class NoteQAResponse(BaseModel):
    answer: str = Field(
        ...,
        min_length=1,
        description="Direct, factual answer derived strictly from the note's content.",
    )

    @field_validator("answer")
    @classmethod
    def clean_answer(cls, v: str) -> str:
        s = v.strip()
        if not s:
            raise ValueError("Answer cannot be empty.")
        return s
