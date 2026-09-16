from uuid import UUID

from fastapi import APIRouter

from app.api.errors import NOT_IMPLEMENTED, unavailable

router = APIRouter(prefix="/incidents", tags=["incidents"])


@router.get("", status_code=501, responses=NOT_IMPLEMENTED)
def list_incidents() -> None:
    unavailable("Incident management")


@router.get("/{incident_id}", status_code=501, responses=NOT_IMPLEMENTED)
def get_incident(incident_id: UUID) -> None:
    unavailable("Incident management")
