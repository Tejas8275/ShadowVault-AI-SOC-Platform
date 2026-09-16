from datetime import datetime
from typing import Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, field_validator


class Change(BaseModel):
    model_config = ConfigDict(extra='forbid')
    before: str | None
    after: str


class Changes(BaseModel):
    model_config = ConfigDict(extra='forbid')
    title: Change | None = None
    description: Change | None = None
    status: Change | None = None
    severity: Change | None = None

    @field_validator('title','description','status','severity')
    @classmethod
    def bounded(cls, change, info):
        if change is None:
            return change
        limits={'title':200,'description':10000,'status':16,'severity':16}
        allowed={'status':{'open','investigating','closed'},'severity':{'low','medium','high','critical'}}
        for value in (change.before,change.after):
            if value is None:
                continue
            if len(value)>limits[info.field_name] or '\x00' in value:
                raise ValueError('Unsupported history value')
            if info.field_name in allowed and value not in allowed[info.field_name]:
                raise ValueError('Unsupported history enum')
        return change


class CaseHistoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    incident_id: UUID
    revision: int
    event_type: Literal['baseline_registered','case_created','case_updated']
    schema_version: int
    actor_type: Literal['user','system']
    actor_user_id: UUID | None
    actor_label: str
    system_actor: str | None
    recorded_at: datetime
    changes: dict[str, Change]
    source: Literal['api','trusted_cli','migration']


class CaseHistoryPage(BaseModel):
    items: list[CaseHistoryResponse]
    tracking_started: bool
    tracking_started_revision: int | None
    next_revision: int | None
