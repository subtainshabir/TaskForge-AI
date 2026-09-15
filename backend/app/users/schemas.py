from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

ThemeLiteral = Literal["light", "dark", "system"]


class ProfileUpdateRequest(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        stripped = value.strip()
        if not stripped:
            raise ValueError("Name cannot be empty")
        return stripped


class UserSettingsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    theme: ThemeLiteral
    created_at: datetime
    updated_at: datetime


class UserSettingsUpdateRequest(BaseModel):
    theme: Optional[ThemeLiteral] = None