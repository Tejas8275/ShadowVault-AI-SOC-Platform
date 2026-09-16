"""Transient, allowlisted metadata draft; no persisted report or conclusions."""
from datetime import datetime
from typing import Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict
from app.schemas.incident import IncidentResponse


class ReportRecord(BaseModel):
    model_config = ConfigDict(extra='forbid')
    citation: str
    evidence_id: UUID | None = None
    fields: dict[str, str | int | None]


class ReportSection(BaseModel):
    title: str
    records: list[ReportRecord]


class CaseReportDraft(BaseModel):
    schema_version: Literal[1] = 1
    status: Literal['draft'] = 'draft'
    generated_at: datetime
    case: IncidentResponse
    scope: Literal['Complete authorized metadata snapshot'] = 'Complete authorized metadata snapshot'
    summary: dict[str, int]
    sections: list[ReportSection]
    limitations: list[str]
