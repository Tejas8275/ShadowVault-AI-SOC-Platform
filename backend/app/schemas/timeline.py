"""Timeline observations are investigator assertions, not automatic forensic findings."""
from datetime import datetime
from typing import Literal
from uuid import UUID
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator, model_validator


class TimelineCreate(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    occurred_at: AwareDatetime
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(default='', max_length=10000)
    source: str = Field(min_length=1, max_length=200)
    source_locator: str | None = Field(default=None, min_length=1, max_length=512)
    submission_id: UUID

    @field_validator('occurred_at', mode='before')
    @classmethod
    def explicit_timestamp(cls, value):
        if not isinstance(value, str) or 'T' not in value:
            raise ValueError('Supply an ISO timestamp with an explicit timezone')
        return value

    @field_validator('title', 'description', 'source', 'source_locator')
    @classmethod
    def plain_text(cls, value):
        if value is not None and '\x00' in value:
            raise ValueError('Text cannot contain NUL characters')
        return value


class TimelineFilters(BaseModel):
    model_config = ConfigDict(extra='forbid')
    incident_id: UUID
    evidence_id: UUID | None = None
    occurred_from: AwareDatetime | None = None
    occurred_to: AwareDatetime | None = None
    q: str | None = Field(default=None, min_length=1, max_length=200)
    origin: Literal['legacy', 'investigator'] | None = None
    sort: Literal['oldest', 'newest'] = 'oldest'
    limit: int = Field(default=50, ge=1, le=100)
    cursor: str | None = Field(default=None, max_length=1024)

    @model_validator(mode='after')
    def ordered(self):
        if self.occurred_from and self.occurred_to and self.occurred_from > self.occurred_to:
            raise ValueError('Range start must not exceed range end')
        return self


class TimelineResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    incident_id: UUID
    evidence_id: UUID | None
    recorded_by_id: UUID
    recorded_by_label: str | None
    occurred_at: datetime
    reported_time: str | None
    created_at: datetime
    title: str
    description: str
    source: str
    source_locator: str | None
    origin: Literal['legacy', 'investigator']
    submission_id: UUID | None


class TimelinePage(BaseModel):
    items: list[TimelineResponse]
    total: int
    next_cursor: str | None
