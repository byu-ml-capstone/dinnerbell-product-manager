from datetime import datetime

from pydantic import BaseModel


class ReviewItemRead(BaseModel):
    id: str
    story_id: str
    story_title: str
    claimed_status: str
    verdict: str
    summary: str
    criteria: list[dict]
    evidence: list[dict]
    has_tests: bool | None
    branch: str | None
    pr_number: int | None
    head_sha: str | None
    reused_from_item_id: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ReviewRead(BaseModel):
    id: str
    sprint_id: str
    status: str
    error: str | None
    model: str
    repo_url: str
    items_total: int
    items_done: int
    summary_markdown: str | None
    unlinked_work: list[dict]
    usage: dict
    created_by_id: str | None
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None

    model_config = {"from_attributes": True}


class ReviewDetail(ReviewRead):
    items: list[ReviewItemRead] = []
