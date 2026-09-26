from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class TaskOverview(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    total_tasks: int = 0
    completed_tasks: int = 0
    in_progress_tasks: int = 0
    todo_tasks: int = 0
    blocked_tasks: int = 0
    cancelled_tasks: int = 0
    average_progress: int = 0


class TaskStatusBreakdown(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    completed: int = 0
    in_progress: int = 0
    todo: int = 0
    blocked: int = 0
    cancelled: int = 0


class DistributionBucket(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    key: str
    label: str
    count: int = 0
    percentage: int = 0


class ProgressDistribution(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    # 5-tier representation
    zero: int = 0
    low: int = 0
    medium: int = 0
    high: int = 0
    complete: int = 0

    # 6-range granular breakdown (0%, 1-24%, 25-49%, 50-74%, 75-99%, 100%)
    p0: int = 0
    p1_24: int = 0
    p25_49: int = 0
    p50_74: int = 0
    p75_99: int = 0
    p100: int = 0

    buckets: List[DistributionBucket] = Field(default_factory=list)


class ProjectProgressSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    status: str
    total_tasks: int = 0
    completed_tasks: int = 0
    in_progress_tasks: int = 0
    todo_tasks: int = 0
    blocked_tasks: int = 0
    cancelled_tasks: int = 0
    average_progress: int = 0
    unfinished_tasks: int = 0


class ProgressAnalyticsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    overview: TaskOverview
    status_breakdown: TaskStatusBreakdown
    progress_distribution: ProgressDistribution
    projects: List[ProjectProgressSummary]
