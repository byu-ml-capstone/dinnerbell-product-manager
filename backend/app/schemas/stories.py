from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field

Status = Literal["backlog", "selected", "in_progress", "blocked", "done"]
Priority = Literal["low", "medium", "high", "urgent"]
# Fibonacci scale (CORE-5); anything else is a 422.
Points = Literal[1, 2, 3, 5, 8, 13]


class StoryCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str = ""
    acceptance_criteria: str = ""
    priority: Priority = "medium"
    story_points: Points | None = None
    assignee_id: str | None = None
    due_date: date | None = None
    sprint_id: str | None = None
    github_branch: str | None = None


class StoryUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    acceptance_criteria: str | None = None
    status: Status | None = None
    priority: Priority | None = None
    story_points: Points | None = None
    assignee_id: str | None = None
    due_date: date | None = None
    sprint_id: str | None = None
    github_branch: str | None = None


class StorySummary(BaseModel):
    id: str
    project_id: str
    sprint_id: str | None
    parent_story_id: str | None
    title: str
    status: str
    priority: str
    story_points: int | None
    assignee_id: str | None
    due_date: date | None
    github_branch: str | None
    blocked_by: list[str] = []
    blocked_by_titles: list[str] = []
    all_blockers_done: bool = False
    subtask_count: int = 0
    carryover_count: int = 0


class StoryWriteResult(StorySummary):
    warnings: list[str] = []


class CommentCreate(BaseModel):
    text: str = Field(min_length=1, max_length=5000)


class CommentRead(BaseModel):
    id: str
    story_id: str
    author_id: str
    author_name: str
    text: str
    created_at: datetime


class DependencyCreate(BaseModel):
    reason: str = Field(default="", max_length=2000)


class DependencyRead(BaseModel):
    id: str
    blocker_story_id: str
    blocked_story_id: str
    blocker_title: str
    blocked_title: str
    blocker_status: str
    reason: str
    created_at: datetime


class DependencyWriteResult(DependencyRead):
    warnings: list[str] = []


class SprintHistoryEntry(BaseModel):
    sprint_id: str | None
    sprint_name: str
    moved_at: datetime
    moved_by_name: str | None


class StoryDetail(StorySummary):
    description: str
    acceptance_criteria: str
    created_at: datetime
    updated_at: datetime
    parent_title: str | None = None
    sprint_name: str | None = None
    sprint_closed: bool = False
    branch_url: str | None = None
    suggested_branch: str
    subtasks: list[StorySummary] = []
    comments: list[CommentRead] = []
    blocks: list[DependencyRead] = []
    blocked_by_links: list[DependencyRead] = []
    sprint_history: list[SprintHistoryEntry] = []
    warnings: list[str] = []


class MoveStoriesRequest(BaseModel):
    story_ids: list[str] = Field(min_length=1)
    sprint_id: str | None = None


class MoveStoriesResult(BaseModel):
    stories: list[StorySummary]
    warnings: list[str] = []


class MoveUnfinishedResult(BaseModel):
    moved: int
    warnings: list[str] = []
