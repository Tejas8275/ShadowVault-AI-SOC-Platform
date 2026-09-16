"""Bounded local normalization; no DNS, file reads or external enrichment."""
from datetime import datetime
from ipaddress import ip_address
import re
import unicodedata
from typing import Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

Kind = Literal['sha256','ip','domain','filename']

def safe_text(value):
    if any(unicodedata.category(c).startswith('C') for c in value):
        raise ValueError('Control characters are not supported')
    return value

def normalize(kind, raw):
    safe_text(raw)
    value=raw.strip()
    if kind=='sha256':
        if not re.fullmatch(r'[0-9a-fA-F]{64}',value): raise ValueError('Enter a 64-character SHA-256 digest')
        return value.lower()
    if kind=='ip':
        if '%' in value: raise ValueError('IP zone identifiers are not supported')
        try: return str(ip_address(value))
        except ValueError: raise ValueError('Enter a single IPv4 or IPv6 address') from None
    if kind=='domain':
        value=value.lower().removesuffix('.')
        labels=value.split('.')
        if len(value)>253 or len(labels)<2 or not re.fullmatch(r'[a-z][a-z0-9-]*',labels[-1]) or any(not re.fullmatch(r'[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?',label) for label in labels):
            raise ValueError('Enter an ASCII domain without a URL, wildcard or IP address')
        return value
    if not raw.strip() or raw in ('.','..') or any(c in raw for c in '/\\:'):
        raise ValueError('Enter a filename, not a path')
    return raw

class IndicatorCreate(BaseModel):
    model_config=ConfigDict(extra='forbid')
    kind: Kind
    source_kind: Literal['manual','evidence_sha256','evidence_filename']='manual'
    raw_value: str | None=Field(default=None,min_length=1,max_length=255)
    source_locator: str | None=Field(default=None,min_length=1,max_length=512)
    submission_id: UUID
    supersedes_id: UUID | None=None

    @field_validator('source_locator')
    @classmethod
    def locator(cls,value):
        return safe_text(value) if value is not None else None

    @model_validator(mode='after')
    def valid_source(self):
        if self.source_kind=='manual':
            if self.raw_value is None: raise ValueError('Manual observations require a value')
            normalize(self.kind,self.raw_value)
        else:
            if self.raw_value is not None or self.source_locator is not None: raise ValueError('Metadata values and locators are server-owned')
            if self.kind != {'evidence_sha256':'sha256','evidence_filename':'filename'}[self.source_kind]: raise ValueError('Indicator kind does not match metadata source')
        return self

class IndicatorResponse(BaseModel):
    model_config=ConfigDict(from_attributes=True)
    id: UUID
    incident_id: UUID
    evidence_id: UUID
    kind: Kind
    raw_value: str
    normalized_value: str
    source_kind: str
    source_locator: str | None
    created_by_id: UUID
    actor_label: str
    created_at: datetime
    schema_version: int
    supersedes_id: UUID | None

class IndicatorListItem(IndicatorResponse):
    superseded_by_id: UUID | None = None

class IndicatorPage(BaseModel):
    items: list[IndicatorListItem]
    next_cursor: str | None=None
