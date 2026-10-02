from typing import List, Optional
from pydantic import BaseModel, Field, field_validator


class NoteImprovementChange(BaseModel):
    category: str = Field(
        ...,
        description="Category of improvement: clarity, grammar, structure, conciseness, or organization.",
    )
    description: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Concise description of the specific improvement made.",
    )

    @field_validator("category", mode="before")
    @classmethod
    def normalize_category(cls, v: Optional[str]) -> str:
        if not v:
            return "clarity"
        val = str(v).strip().lower()
        if val in ("clarity", "grammar", "structure", "conciseness", "organization"):
            return val
        if "clear" in val or "clarif" in val or "readab" in val:
            return "clarity"
        if "gramm" in val or "spell" in val or "punct" in val:
            return "grammar"
        if "struct" in val or "format" in val or "layout" in val:
            return "structure"
        if "concis" in val or "brev" in val or "short" in val or "repet" in val:
            return "conciseness"
        if "organ" in val or "order" in val or "group" in val:
            return "organization"
        return "clarity"

    @field_validator("description")
    @classmethod
    def clean_description(cls, v: str) -> str:
        s = v.strip()
        if not s:
            raise ValueError("Change description cannot be empty")
        return s[:500]


class NoteImprovementResponse(BaseModel):
    improved_title: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Improved, clear, and descriptive note title.",
    )
    improved_content: str = Field(
        ...,
        min_length=1,
        description="Suggested improved note content with enhanced clarity, structure, and grammar.",
    )
    changes: List[NoteImprovementChange] = Field(
        default_factory=list,
        description="List of concrete improvements made to the note.",
    )
    warnings: List[str] = Field(
        default_factory=list,
        description="Important warnings or notes regarding preserved facts, ambiguous context, or limits.",
    )

    @field_validator("improved_title")
    @classmethod
    def clean_title(cls, v: str) -> str:
        s = v.strip()
        if not s:
            raise ValueError("Improved title cannot be empty")
        return s[:255]

    @field_validator("improved_content")
    @classmethod
    def clean_content(cls, v: str) -> str:
        s = v.strip()
        if not s:
            raise ValueError("Improved content cannot be empty")
        return s
