from uuid import UUID

from fastapi import APIRouter

from app.api.errors import NOT_IMPLEMENTED, unavailable

router = APIRouter(prefix="/timeline", tags=["timeline"])


@router.get("", status_code=501, responses=NOT_IMPLEMENTED)
def list_timeline_events(incident_id: UUID | None = None) -> None:
    unavailable("Timeline reconstruction")


@router.get("/{event_id}", status_code=501, responses=NOT_IMPLEMENTED)
def get_timeline_event(event_id: UUID) -> None:
    unavailable("Timeline reconstruction")
