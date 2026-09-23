from typing import List
from pydantic import BaseModel, ConfigDict, Field


class TaskAnalysisResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    summary: str = Field(description="Clear, concise summary of what the task entails")
    goal: str = Field(description="Primary objective and outcome of completing this task")
    category: str = Field(description="Domain or functional area of the task")
    complexity: str = Field(description="Estimated complexity level: Low, Medium, or High")
    skills: List[str] = Field(default_factory=list, description="Relevant technical or domain skills required")
    potential_challenges: List[str] = Field(
        default_factory=list, description="Potential obstacles, edge cases, or challenges"
    )
