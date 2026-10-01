from typing import List, Optional
from pydantic import BaseModel, Field


class ActionItem(BaseModel):
    title: str = Field(
        ...,
        description="Actionable item, to-do, or task extracted from the note.",
    )
    details: Optional[str] = Field(
        None,
        description="Optional extra context, instructions, or sub-details.",
    )
    priority: Optional[str] = Field(
        None,
        description="Priority if explicitly stated or clearly implied ('high', 'medium', 'low', or null).",
    )


class ExtractedDate(BaseModel):
    text: str = Field(
        ...,
        description="The date or deadline text as written in the note (e.g., 'October 15', 'next Friday').",
    )
    date: Optional[str] = Field(
        None,
        description="Normalized ISO date (YYYY-MM-DD) ONLY if the year and date are clearly determinable; otherwise null.",
    )
    context: Optional[str] = Field(
        None,
        description="The event, task, or context associated with this date.",
    )


class NoteExtractionResponse(BaseModel):
    action_items: List[ActionItem] = Field(
        default_factory=list,
        description="Actionable tasks, checklist items, or to-dos identified in the note.",
    )
    decisions: List[str] = Field(
        default_factory=list,
        description="Explicit decisions, agreements, or architectural choices made in the note (distinct from suggestions).",
    )
    important_facts: List[str] = Field(
        default_factory=list,
        description="Important factual information, constraints, requirements, or architecture points stated in the note.",
    )
    dates: List[ExtractedDate] = Field(
        default_factory=list,
        description="Dates, deadlines, or milestones explicitly mentioned in the note.",
    )
    people: List[str] = Field(
        default_factory=list,
        description="Names of people, stakeholders, roles, or organizations explicitly mentioned in the note.",
    )
    technical_terms: List[str] = Field(
        default_factory=list,
        description="Key technologies, frameworks, APIs, protocols, or domain terminology mentioned in the note.",
    )
    follow_ups: List[str] = Field(
        default_factory=list,
        description="Follow-up items, open questions, future investigations, or things to verify later.",
    )
