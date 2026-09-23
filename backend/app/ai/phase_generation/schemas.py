from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class AIGeneratedPhaseItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    title: str = Field(min_length=1, max_length=255, description="Clear, actionable title of the phase")
    description: Optional[str] = Field(
        default=None, max_length=2000, description="Concise description of the work in this phase"
    )


class AIGeneratedPhasesResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    phases: List[AIGeneratedPhaseItem] = Field(
        min_length=1, description="List of sequential, independently completable implementation phases"
    )
