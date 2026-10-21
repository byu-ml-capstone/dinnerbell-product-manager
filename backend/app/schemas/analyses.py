from datetime import datetime

from pydantic import BaseModel, Field


class AnalysisCreate(BaseModel):
    additional_context: str = Field(default="", max_length=5000)


class AnalysisSave(BaseModel):
    final_content: str = Field(min_length=1)


class AnalysisRead(BaseModel):
    id: str
    sprint_id: str
    trigger: str
    status: str
    error: str | None
    model: str
    additional_context: str
    ai_content: str | None
    final_content: str | None
    created_by_id: str | None
    created_by_name: str | None
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    finalized_at: datetime | None
    finalized_by_id: str | None
    finalized_by_name: str | None


class AnalysisDetail(AnalysisRead):
    input_snapshot: dict
    metrics: dict
    usage: dict | None
