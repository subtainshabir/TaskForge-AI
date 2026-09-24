from typing import Any, List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

TaskPriorityLiteral = Literal["low", "medium", "high", "urgent"]


class TaskPriorityAnalysisResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    current_priority: TaskPriorityLiteral
    recommended_priority: TaskPriorityLiteral
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence score between 0.0 and 1.0")
    reasoning: str = Field(description="Clear explanation of why this priority is recommended")
    factors: List[str] = Field(default_factory=list, description="Key factors contributing to the recommendation")
    is_inconsistent: Optional[bool] = Field(
        default=None, description="Whether current priority appears inconsistent with context"
    )

    @field_validator("confidence", mode="before")
    @classmethod
    def clamp_confidence(cls, v: Any) -> float:
        if v is None:
            return 0.8
        if isinstance(v, str):
            v = v.replace("%", "").strip()
        try:
            val = float(v)
        except (ValueError, TypeError):
            val = 0.8
        if val < 0.0:
            return 0.0
        if val > 1.0:
            if val <= 100.0:
                return round(val / 100.0, 2)
            return 1.0
        return round(val, 2)

    @field_validator("current_priority", "recommended_priority", mode="before")
    @classmethod
    def validate_priority(cls, v: Any) -> str:
        s = str(v).strip().lower()
        if s not in ("low", "medium", "high", "urgent"):
            raise ValueError(f"Invalid priority '{v}'. Must be low, medium, high, or urgent.")
        return s

    @field_validator("factors", mode="before")
    @classmethod
    def validate_factors(cls, v: Any) -> List[str]:
        if v is None:
            return []
        if isinstance(v, str):
            return [line.strip("- *").strip() for line in v.splitlines() if line.strip()]
        if isinstance(v, list):
            return [str(item).strip() for item in v if str(item).strip()]
        return []

    @model_validator(mode="after")
    def populate_inconsistent(self):
        if self.is_inconsistent is None:
            self.is_inconsistent = self.recommended_priority != self.current_priority
        return self
