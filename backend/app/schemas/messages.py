from datetime import datetime

from pydantic import BaseModel, Field


class MessageCreate(BaseModel):
    text: str = Field(min_length=1, max_length=5000)
    parent_message_id: str | None = None


class MessageUpdate(BaseModel):
    text: str = Field(min_length=1, max_length=5000)


class MessageRead(BaseModel):
    id: str
    sprint_id: str
    author_id: str
    author_name: str
    parent_message_id: str | None
    text: str
    created_at: datetime
    edited_at: datetime | None
    replies: list["MessageRead"] = []
