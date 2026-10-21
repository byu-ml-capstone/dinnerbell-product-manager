from datetime import date, datetime

from pydantic import BaseModel

from .sprints import SprintRead
from .stories import StorySummary


class VelocitySprint(BaseModel):
    id: str
    name: str
    start_date: date
    end_date: date
    committed_points: int | None
    velocity: int
    closed_at: datetime | None


class VelocityRead(BaseModel):
    sprints: list[VelocitySprint]
    average_velocity_3: float | None


class BurndownPoint(BaseModel):
    date: date
    remaining_points: int
    ideal_points: float
    scope_change_points: int


class SprintMetrics(BaseModel):
    committed_points: int | None
    completed_points: int
    remaining_points: int
    percent_complete: float | None
    scope_added_points: int
    scope_removed_points: int
    days_elapsed: int
    days_remaining: int
    unpointed_story_count: int
    points_per_day: float | None
    estimated_completion_date: date | None
    burndown: list[BurndownPoint]


class PlanningSprint(BaseModel):
    sprint: SprintRead
    stories: list[StorySummary]
    capacity_warning: str | None


class ClosedWithUnfinished(BaseModel):
    sprint: SprintRead
    unfinished_count: int


class PlanningRead(BaseModel):
    backlog: list[StorySummary]
    sprints: list[PlanningSprint]
    closed_with_unfinished: list[ClosedWithUnfinished]
