"""Bounded collection contracts; a manifest is approved before an agent uploads."""
from datetime import datetime
from pathlib import PureWindowsPath
from typing import Literal
from uuid import UUID
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator


class AgentRegistration(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    name: str = Field(min_length=1, max_length=120)
    platform: Literal["windows"] = "windows"
    collector_version: str = Field(default="0.1.0", min_length=1, max_length=32)


class RegisteredAgent(BaseModel):
    id: UUID
    name: str
    token: str
    token_expires_at: datetime


class SelectedFile(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source_path: str = Field(min_length=1, max_length=1024)
    max_bytes: int = Field(gt=0)

    @field_validator("source_path")
    @classmethod
    def local_windows_file(cls, value: str) -> str:
        path = PureWindowsPath(value)
        reserved = {'CON', 'PRN', 'AUX', 'NUL', 'CONIN$', 'CONOUT$'}
        reserved |= {f'{prefix}{suffix}' for prefix in ('COM', 'LPT') for suffix in '123456789¹²³'}
        if (not path.is_absolute() or len(path.drive) != 2 or path.drive[1] != ':'
            or '..' in path.parts or any(part.split('.')[0].rstrip().upper() in reserved for part in path.parts[1:])
            or any(c in value for c in '*?<>|"')
            or any(ord(c) < 32 for c in value) or ':' in str(path)[2:]
            or not 1 <= len(path.name) <= 255 or value.endswith(('\\', '/'))
            or any(part.endswith((' ', '.')) for part in path.parts[1:])):
            raise ValueError("Select an absolute local Windows file path; no wildcards, devices, UNC paths or streams")
        return str(path)


class JobRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    incident_id: UUID
    agent_id: UUID
    files: list[SelectedFile] = Field(min_length=1, max_length=100)

    @field_validator("files")
    @classmethod
    def unique_files(cls, value):
        if len({file.source_path.casefold() for file in value}) != len(value):
            raise ValueError("Each selected file must be unique")
        return value


class ManifestFile(SelectedFile):
    id: UUID


class JobResponse(BaseModel):
    id: UUID
    incident_id: UUID
    agent_id: UUID
    status: str
    files: list[ManifestFile]
    completed_files: int


class UploadMetadata(BaseModel):
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    size_bytes: int = Field(ge=0)
    collected_at: AwareDatetime


class EvidenceReceipt(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    incident_id: UUID
    collection_job_id: UUID
    collection_item_id: UUID
    filename: str
    source_path: str
    size_bytes: int
    sha256: str
    collected_at: datetime
    verified_at: datetime
    verification_status: Literal["verified"]
