from typing import List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator

PhaseRefinementType = Literal["add", "rename", "update_description", "remove", "reorder", "split"]


class SplitPhaseItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    title: str = Field(min_length=1, max_length=255)
    description: Optional[str] = Field(default=None, max_length=2000)

    @field_validator("title")
    @classmethod
    def strip_title(cls, v: str) -> str:
        s = v.strip()
        if not s:
            raise ValueError("Title cannot be empty")
        return s


class PhaseRefinementSuggestion(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: Optional[str] = Field(default=None, description="Unique identifier for suggestion selection")
    type: PhaseRefinementType
    phase_id: Optional[int] = Field(default=None, description="Target phase ID for existing phases")
    title: Optional[str] = Field(default=None, max_length=255, description="Current phase title or title")
    description: Optional[str] = Field(default=None, max_length=2000, description="Rationale or notes")
    proposed_title: Optional[str] = Field(default=None, max_length=255, description="Proposed new title")
    proposed_description: Optional[str] = Field(default=None, max_length=2000, description="Proposed description")
    proposed_order: Optional[int] = Field(default=None, ge=0, description="Target order index")
    split_phases: Optional[List[SplitPhaseItem]] = Field(
        default=None, description="List of replacement phases when splitting an existing phase"
    )

    @field_validator("proposed_title", "title")
    @classmethod
    def strip_titles(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        s = v.strip()
        return s if s else None


class PhaseRefinementResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    summary: str = Field(description="Summary of the review and improvement suggestions")
    suggestions: List[PhaseRefinementSuggestion] = Field(default_factory=list)


class ApplyRefinementsRequest(BaseModel):
    suggestions: List[PhaseRefinementSuggestion] = Field(min_length=1)
