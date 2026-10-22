from pydantic import BaseModel


class PullRequestInfo(BaseModel):
    number: int
    title: str
    state: str
    merged: bool
    url: str


class StoryGitHubStatus(BaseModel):
    branch: str
    branch_url: str | None
    branch_exists: bool
    pull_request: PullRequestInfo | None
