from typing import List, Optional

from sqlalchemy import CheckConstraint
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import WorkStatus
from app.models.mixins import TimestampMixin


class Phase(Base, TimestampMixin):
    __tablename__ = "phases"
    __table_args__ = (
        CheckConstraint("progress >= 0 AND progress <= 100", name="ck_phases_progress_range"),
        CheckConstraint("order_index >= 0", name="ck_phases_order_index_nonneg"),
        CheckConstraint("estimated_minutes >= 0", name="ck_phases_estimated_minutes_nonneg"),
        CheckConstraint("actual_minutes >= 0", name="ck_phases_actual_minutes_nonneg"),
        Index("ix_phases_task_order", "task_id", "order_index"),
        Index("ix_phases_task_status", "task_id", "status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[int] = mapped_column(
        ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[WorkStatus] = mapped_column(
        SQLEnum(WorkStatus, name="work_status", values_callable=lambda e: [m.value for m in e]),
        nullable=False,
        default=WorkStatus.TODO,
        index=True,
    )
    progress: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    estimated_minutes: Mapped[Optional[int]] = mapped_column(Integer)
    actual_minutes: Mapped[Optional[int]] = mapped_column(Integer)

    task: Mapped["Task"] = relationship(back_populates="phases")
    subtasks: Mapped[List["Subtask"]] = relationship(
        back_populates="phase",
        cascade="all, delete-orphan",
        order_by="Subtask.order_index",
        lazy="selectin",
    )