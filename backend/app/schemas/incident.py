"""Case contracts reuse Incident identity; owner and revision are server controlled."""
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, field_validator
from app.models.incident import IncidentStatus, Severity


class IncidentCreate(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(default='', max_length=10000)
    severity: Severity = Severity.MEDIUM

    @field_validator('title', 'description')
    @classmethod
    def no_nul(cls, value):
        if '\x00' in value: raise ValueError('NUL characters are not supported')
        return value


class IncidentUpdate(IncidentCreate):
    expected_revision: int = Field(ge=0, strict=True)
    status: IncidentStatus


class IncidentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    title: str
    description: str
    severity: Severity
    status: IncidentStatus
    created_by_id: UUID
    created_at: datetime
    updated_at: datetime | None
    revision: int


class IncidentFilters(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    q: str | None = Field(default=None, min_length=1, max_length=200)
    status: IncidentStatus | None = None
    severity: Severity | None = None
    limit: int = Field(default=50, ge=1, le=100)
    cursor: str | None = Field(default=None, max_length=1024)


class IncidentPage(BaseModel):
    items: list[IncidentResponse]
    total: int
    next_cursor: str | None


class CaseIntelligence(BaseModel):
    evidence_count: int
    timeline_count: int
    history_revision_count: int
    history_started_revision: int | None
    latest_activity_at: datetime


class IncidentDetail(IncidentResponse):
    intelligence: CaseIntelligence | None = None
