"""Extractive model selections; displayed values are resolved only by the server."""
from datetime import datetime
from typing import Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class BriefingRequest(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    schema_version: Literal[1] = 1


class ModelSelection(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    sources: list[str] = Field(min_length=1, max_length=20)


class BriefingSource(BaseModel):
    citation: str
    section: str
    evidence_id: UUID | None = None
    fields: dict[str, str | int | None]
    selection: Literal['model', 'correction_context'] = 'model'


class CaseBriefing(BaseModel):
    schema_version: Literal[1] = 1
    kind: Literal['ai_selected_metadata'] = 'ai_selected_metadata'
    case_id: UUID
    case_title: str
    case_revision: int
    snapshot_at: datetime
    context_sha256: str
    prompt_version: Literal['metadata-selection-v1'] = 'metadata-selection-v1'
    sources: list[BriefingSource]
    limitations: list[str]
