from datetime import date, datetime

from pydantic import BaseModel, Field, model_validator


class SprintCreate(BaseModel):
    name: str | None = Field(default=None, max_length=255)
    goal: str = ""
    start_date: date
    end_date: date

    @model_validator(mode="after")
    def check_dates(self):
        if self.end_date < self.start_date:
            raise ValueError("end_date must be on or after start_date")
        return self


class SprintUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    goal: str | None = None
    start_date: date | None = None
    end_date: date | None = None


class SprintRead(BaseModel):
    id: str
    project_id: str
    name: str
    goal: str
    status: str
    is_overdue: bool
    start_date: date
    end_date: date
    closed_at: datetime | None
    closed_by_id: str | None
    velocity: int | None
    committed_points: int | None
    notes: str
    story_count: int
    planned_points: int
    completed_points: int
    # MOVE-9: planned points above the 3-sprint average velocity (open sprints only).
    capacity_warning: str | None = None
    created_at: datetime


class SprintClose(BaseModel):
    notes: str = ""


class SprintCloseResult(BaseModel):
    id: str
    status: str
    closed_at: datetime
    velocity: int
    committed_points: int | None
    completed_stories: int
    incomplete_stories: int
    unpointed_done_stories: int
    analysis_id: str | None


class MoveUnfinishedRequest(BaseModel):
    target_sprint_id: str | None = None
