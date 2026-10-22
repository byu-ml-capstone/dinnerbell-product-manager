from datetime import datetime

from pydantic import BaseModel


class DeleteResult(BaseModel):
    batch_id: str
    counts: dict[str, int]


class TrashItem(BaseModel):
    batch_id: str
    project_id: str
    root_type: str
    root_id: str
    root_label: str
    counts: dict[str, int]
    deleted_by: str | None
    deleted_at: datetime


class RestoreResult(BaseModel):
    batch_id: str
    root_type: str
    root_id: str
    restored: dict[str, int]
