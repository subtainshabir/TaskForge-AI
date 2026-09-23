from datetime import datetime
from typing import List, Optional

from sqlalchemy import CheckConstraint, DateTime
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import TaskPriority, WorkStatus
from app.models.mixins import TimestampMixin


class Task(Base, TimestampMixin):
    __tablename__ = "tasks"
    __table_args__ = (
        CheckConstraint("progress >= 0 AND progress <= 100", name="ck_tasks_progress_range"),
        CheckConstraint("estimated_minutes >= 0", name="ck_tasks_estimated_minutes_nonneg"),
        CheckConstraint("actual_minutes >= 0", name="ck_tasks_actual_minutes_nonneg"),
        Index("ix_tasks_user_status", "user_id", "status"),
        Index("ix_tasks_project_status", "project_id", "status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    status: Mapped[WorkStatus] = mapped_column(
        SQLEnum(WorkStatus, name="work_status", values_callable=lambda e: [m.value for m in e]),
        nullable=False,
        default=WorkStatus.TODO,
        index=True,
    )
    priority: Mapped[TaskPriority] = mapped_column(
        SQLEnum(TaskPriority, name="task_priority", values_callable=lambda e: [m.value for m in e]),
        nullable=False,
        default=TaskPriority.MEDIUM,
        index=True,
    )
    deadline: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), index=True)
    estimated_minutes: Mapped[Optional[int]] = mapped_column(Integer)
    actual_minutes: Mapped[Optional[int]] = mapped_column(Integer)
    progress: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    project: Mapped["Project"] = relationship(back_populates="tasks")
    user: Mapped["User"] = relationship()
    phases: Mapped[List["Phase"]] = relationship(
        back_populates="task",
        cascade="all, delete-orphan",
        order_by="Phase.order_index",
        lazy="selectin",
    )
    notes: Mapped[List["Note"]] = relationship(back_populates="task")
    conversations: Mapped[List["Conversation"]] = relationship(back_populates="task")
    dependencies: Mapped[List["TaskDependency"]] = relationship(
        "TaskDependency",
        foreign_keys="TaskDependency.task_id",
        back_populates="task",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    dependents: Mapped[List["TaskDependency"]] = relationship(
        "TaskDependency",
        foreign_keys="TaskDependency.depends_on_task_id",
        back_populates="depends_on_task",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    activities: Mapped[List["TaskActivity"]] = relationship(
        "TaskActivity",
        back_populates="task",
        cascade="all, delete-orphan",
        order_by="TaskActivity.created_at.desc()",
        lazy="selectin",
    )

    @property
    def is_blocked(self) -> bool:
        if not self.dependencies:
            return False
        return any(
            dep.depends_on_task is not None
            and dep.depends_on_task.status not in (WorkStatus.COMPLETED, WorkStatus.CANCELLED)
            for dep in self.dependencies
        )

    @property
    def project_name(self) -> Optional[str]:
        return self.project.name if self.project else None