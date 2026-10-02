from typing import List
from pydantic import BaseModel, Field, field_validator


class NoteSearchSource(BaseModel):
    note_id: int = Field(..., description="ID of the cited note")
    title: str = Field(..., description="Title of the cited note")


class NoteAISearchRequest(BaseModel):
    question: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="Question to ask across the user's notes.",
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


class NoteAISearchResponse(BaseModel):
    answer: str = Field(
        ...,
        min_length=1,
        description="Direct factual answer synthesized from relevant notes, or statement of unavailability.",
    )
    sources: List[NoteSearchSource] = Field(
        default_factory=list,
        description="List of notes that served as sources for the answer.",
    )
