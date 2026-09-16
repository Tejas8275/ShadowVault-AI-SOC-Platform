from uuid import UUID

from fastapi import APIRouter

from app.api.errors import NOT_IMPLEMENTED, unavailable

router = APIRouter(prefix="/evidence", tags=["evidence"])


@router.get("", status_code=501, responses=NOT_IMPLEMENTED)
def list_evidence(incident_id: UUID | None = None) -> None:
    unavailable("Evidence management")


@router.get("/{evidence_id}", status_code=501, responses=NOT_IMPLEMENTED)
def get_evidence(evidence_id: UUID) -> None:
    unavailable("Evidence management")
