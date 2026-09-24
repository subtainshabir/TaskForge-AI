from typing import Any, List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

SeverityLiteral = Literal["low", "medium", "high"]


def clamp_score(v: Any, default: int = 50) -> int:
    if v is None:
        return default
    if isinstance(v, str):
        v = v.replace("%", "").strip()
    try:
        val = float(v)
    except (ValueError, TypeError):
        return default
    if val <= 1.0 and val > 0:
        val = val * 100
    val_int = int(round(val))
    return max(0, min(100, val_int))


class TaskQualityDimension(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str = Field(description="Name of quality dimension, e.g. clarity, specificity, actionability, completeness, context")
    score: int = Field(ge=0, le=100, description="Score from 0 to 100")
    explanation: str = Field(description="Brief explanation of this dimension score")

    @field_validator("score", mode="before")
    @classmethod
    def validate_score(cls, v: Any) -> int:
        return clamp_score(v, default=50)

    @field_validator("name", mode="before")
    @classmethod
    def validate_name(cls, v: Any) -> str:
        return str(v).strip().lower()


class TaskQualityIssue(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    title: str = Field(description="Short title of the quality issue")
    description: str = Field(description="Explanation of the issue")
    severity: SeverityLiteral = Field(default="medium", description="Severity level: low, medium, high")

    @field_validator("severity", mode="before")
    @classmethod
    def validate_severity(cls, v: Any) -> str:
        s = str(v).strip().lower() if v is not None else "medium"
        if s not in ("low", "medium", "high"):
            return "medium"
        return s


class TaskQualitySuggestion(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    title: str = Field(description="Actionable suggestion title")
    description: str = Field(description="Detailed guidance on how to improve the task definition")


class TaskQualityResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    overall_score: int = Field(ge=0, le=100, description="Overall quality score from 0 to 100")
    summary: str = Field(description="Executive summary of the task quality assessment")
    dimensions: List[TaskQualityDimension] = Field(default_factory=list, description="Scores for individual quality dimensions")
    issues: List[TaskQualityIssue] = Field(default_factory=list, description="Identified quality issues or ambiguities")
    suggestions: List[TaskQualitySuggestion] = Field(default_factory=list, description="Concrete suggestions to improve task quality")

    @field_validator("overall_score", mode="before")
    @classmethod
    def validate_overall_score(cls, v: Any) -> int:
        return clamp_score(v, default=60)

    @model_validator(mode="after")
    def calculate_fallback_score(self):
        # If overall score is somehow default and dimensions are present, ensure it's aligned
        if self.dimensions and self.overall_score == 0:
            avg = sum(d.score for d in self.dimensions) / len(self.dimensions)
            self.overall_score = max(0, min(100, int(round(avg))))
        return self
