"""Additive investigation contracts. Acquisition fields are never accepted as edits."""
import re
from datetime import datetime
from typing import Literal
from uuid import UUID
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator, model_validator

ReviewState = Literal["unreviewed", "in_review", "reviewed"]
IntegrityResult = Literal["not_checked", "matches", "mismatch", "missing", "unavailable"]


def normalize_tags(values):
    normalized = sorted({value.strip().lower() for value in values})
    if any(re.fullmatch(r"[a-z0-9][a-z0-9._-]{0,63}", value) is None for value in normalized):
        raise ValueError("Tags must be 1–64 ASCII letters, digits, dots, underscores or hyphens")
    return normalized


class EvidenceFilters(BaseModel):
    model_config = ConfigDict(extra="forbid")
    incident_id: UUID | None = None
    collection_job_id: UUID | None = None
    agent_id: UUID | None = None
    q: str | None = Field(default=None, min_length=1, max_length=200)
    sha256: str | None = Field(default=None, pattern=r"^[0-9a-fA-F]{64}$")
    tags: list[str] = Field(default_factory=list, max_length=20)
    review_state: ReviewState | None = None
    verification_status: Literal["legacy", "verified"] | None = None
    integrity_result: IntegrityResult | None = None
    created_from: AwareDatetime | None = None
    created_to: AwareDatetime | None = None
    collected_from: AwareDatetime | None = None
    collected_to: AwareDatetime | None = None
    min_size: int | None = Field(default=None, ge=0)
    max_size: int | None = Field(default=None, ge=0)
    sort: Literal["newest", "oldest"] = "newest"
    limit: int = Field(default=50, ge=1, le=100)
    cursor: str | None = Field(default=None, max_length=1024)

    @field_validator("tags")
    @classmethod
    def tags_valid(cls, values):
        return normalize_tags(values)

    @model_validator(mode="after")
    def ordered_ranges(self):
        for start, end in [(self.created_from, self.created_to), (self.collected_from, self.collected_to),
                           (self.min_size, self.max_size)]:
            if start is not None and end is not None and start > end:
                raise ValueError("Range start must not exceed range end")
        return self


class AnnotationPatch(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    expected_revision: int = Field(ge=0)
    display_title: str | None = Field(default=None, min_length=1, max_length=200)
    review_state: ReviewState | None = None
    tags: list[str] | None = Field(default=None, max_length=20)

    @field_validator("tags")
    @classmethod
    def tags_valid(cls, values):
        return normalize_tags(values) if values is not None else None

    @model_validator(mode="after")
    def meaningful_edit(self):
        if not self.model_fields_set.intersection({"display_title", "review_state", "tags"}):
            raise ValueError("Supply at least one annotation field")
        if "review_state" in self.model_fields_set and self.review_state is None:
            raise ValueError("Review state cannot be null")
        if "tags" in self.model_fields_set and self.tags is None:
            raise ValueError("Use an empty list to clear tags")
        return self


class NoteCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    expected_revision: int = Field(ge=0)
    body: str = Field(min_length=1, max_length=10000)

    @field_validator("body")
    @classmethod
    def no_nul(cls, value):
        if '\x00' in value:
            raise ValueError("Notes cannot contain NUL characters")
        return value


class EvidenceSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    incident_id: UUID
    collection_job_id: UUID | None
    collection_item_id: UUID | None
    filename: str
    display_title: str | None
    source_path: str | None
    media_type: str
    size_bytes: int
    sha256: str
    created_at: datetime
    collected_at: datetime | None
    initial_verification_status: str = Field(validation_alias="verification_status")
    initial_verified_at: datetime | None = Field(validation_alias="verified_at")
    review_state: ReviewState
    metadata_revision: int
    tags: list[str] = Field(default_factory=list)
    integrity_result: IntegrityResult = "not_checked"
    integrity_checked_at: datetime | None = None
    custody_started: bool = False


class EvidenceDetails(EvidenceSummary):
    collected_by_user_id: UUID
    requested_by_user_id: UUID | None
    agent_id: UUID | None
    custody_sequence: int
    custody_head_hash: str | None
    note_count: int


class SearchPage(BaseModel):
    items: list[EvidenceSummary]
    total: int
    next_cursor: str | None


class CustodyEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    evidence_id: UUID
    sequence: int
    schema_version: int
    event_type: str
    actor_type: str
    actor_user_id: UUID | None
    actor_agent_id: UUID | None
    system_actor: str | None
    actor_label: str
    recorded_at: datetime
    source_at: datetime | None
    operation_id: UUID
    details: dict
    previous_hash: str | None
    event_hash: str


class CustodyPage(BaseModel):
    items: list[CustodyEventResponse]
    tracking_started: bool
    head_sequence: int
    head_hash: str | None
    next_sequence: int | None


class NoteResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    evidence_id: UUID
    author_id: UUID
    author_label: str
    body: str
    created_at: datetime


class NoteReceipt(BaseModel):
    note: NoteResponse
    metadata_revision: int


class NotesPage(BaseModel):
    items: list[NoteResponse]
    next_cursor: str | None
