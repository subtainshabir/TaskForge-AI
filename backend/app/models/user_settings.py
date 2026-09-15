from sqlalchemy import Enum as SQLEnum
from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import ThemePreference
from app.models.mixins import TimestampMixin


class UserSettings(Base, TimestampMixin):
    __tablename__ = "user_settings"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True, index=True
    )
    theme: Mapped[ThemePreference] = mapped_column(
        SQLEnum(ThemePreference, name="theme_preference", values_callable=lambda e: [m.value for m in e]),
        nullable=False,
        default=ThemePreference.SYSTEM,
    )

    user: Mapped["User"] = relationship(back_populates="settings")