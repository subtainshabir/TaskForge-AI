from typing import List
from pydantic import BaseModel, Field


class NoteSummaryResponse(BaseModel):
    summary: str = Field(
        ...,
        description="A concise 1-3 sentence summary synthesizing the core content of the note.",
    )
    key_points: List[str] = Field(
        default_factory=list,
        description="Key takeaways, concepts, or highlights from the note.",
    )
    action_items: List[str] = Field(
        default_factory=list,
        description="Actionable tasks, checklist items, or to-dos identified in the note.",
    )
    important_details: List[str] = Field(
        default_factory=list,
        description="Important constraints, technical details, dates, metrics, or references.",
    )
