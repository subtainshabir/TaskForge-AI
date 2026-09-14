from datetime import datetime
from typing import Optional

from sqlalchemy import CheckConstraint, DateTime
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import WorkStatus
from app.models.mixins import TimestampMixin


class Subtask(Base, TimestampMixin):
    __tablename__ = "subtasks"
    __table_args__ = (
        Index("ix_subtasks_phase_order", "phase_id", "order_index"),
        CheckConstraint("order_index >= 0", name="ck_subtasks_order_index_nonneg"),
        CheckConstraint("estimated_minutes >= 0", name="ck_subtasks_estimated_minutes_nonneg"),
        CheckConstraint("actual_minutes >= 0", name="ck_subtasks_actual_minutes_nonneg"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    phase_id: Mapped[int] = mapped_column(
        ForeignKey("phases.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    status: Mapped[WorkStatus] = mapped_column(
        SQLEnum(WorkStatus, name="work_status", values_callable=lambda e: [m.value for m in e]),
        nullable=False,
        default=WorkStatus.TODO,
        index=True,
    )
    order_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    estimated_minutes: Mapped[Optional[int]] = mapped_column(Integer)
    actual_minutes: Mapped[Optional[int]] = mapped_column(Integer)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    phase: Mapped["Phase"] = relationship(back_populates="subtasks")