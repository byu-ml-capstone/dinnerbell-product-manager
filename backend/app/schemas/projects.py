from datetime import datetime

from pydantic import BaseModel, Field

from .auth import UserRead
from .sprints import SprintRead


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str = ""
    team_member_ids: list[str] = []


class ProjectUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    github_repo_url: str | None = None


class ProjectRead(BaseModel):
    id: str
    name: str
    description: str
    owner_id: str
    github_repo_url: str | None
    created_at: datetime
    members: list[UserRead] = []


class TeamMemberAdd(BaseModel):
    user_id: str
    # Ignored: there is one role (PERM-1). Accepted so older clients don't break.
    role: str = "member"


class ProjectSummary(BaseModel):
    counts: dict[str, int]
    total_stories: int
    active_sprints: list[SprintRead]
