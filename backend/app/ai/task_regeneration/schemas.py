from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator


class TaskRegenerateRequest(BaseModel):
    instruction: Optional[str] = Field(
        default=None,
        max_length=1000,
        description="Optional custom improvement guidance or instruction",
    )

    @field_validator("instruction", mode="before")
    @classmethod
    def clean_instruction(cls, v: object) -> Optional[str]:
        if v is None:
            return None
        s = str(v).strip()
        return s if s else None


class TaskRegenerateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    title: str = Field(
        min_length=1,
        max_length=255,
        description="Improved, specific, and actionable task title",
    )
    description: str = Field(
        min_length=1,
        max_length=5000,
        description="Clear, comprehensive, and actionable task description",
    )
    changes: List[str] = Field(
        default_factory=list,
        description="Summary of specific improvements made to the task",
    )

    @field_validator("title", mode="before")
    @classmethod
    def clean_title(cls, v: object) -> str:
        if v is None:
            raise ValueError("Regenerated title cannot be empty")
        s = str(v).strip().strip("\"' ")
        if s.lower().startswith("title:"):
            s = s[6:].strip()
        s = s.strip("\"' ")
        if not s:
            raise ValueError("Regenerated title cannot be empty")
        return s[:255]

    @field_validator("description", mode="before")
    @classmethod
    def clean_description(cls, v: object) -> str:
        if v is None:
            raise ValueError("Regenerated description cannot be empty")
        s = str(v).strip().strip("\"' ")
        if s.lower().startswith("description:"):
            s = s[12:].strip()
        s = s.strip("\"' ")
        if not s:
            raise ValueError("Regenerated description cannot be empty")
        return s[:5000]

    @field_validator("changes", mode="before")
    @classmethod
    def clean_changes(cls, v: object) -> List[str]:
        if v is None:
            return []
        if isinstance(v, list):
            cleaned = []
            for item in v:
                if item:
                    item_str = str(item).strip()
                    if item_str:
                        cleaned.append(item_str)
            return cleaned
        s = str(v).strip()
        return [s] if s else []
