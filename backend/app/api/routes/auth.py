"""Authentication contract only; no credentials are checked or tokens issued."""

from fastapi import APIRouter

from app.api.errors import NOT_IMPLEMENTED, unavailable
from app.schemas.auth import LoginRequest

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post("/login", status_code=501, responses=NOT_IMPLEMENTED)
def login(payload: LoginRequest) -> None:
    unavailable("Sign-in")


@router.get("/me", status_code=501, responses=NOT_IMPLEMENTED)
def current_user() -> None:
    unavailable("User sessions")
