"""Explicit responses for domain operations beyond the foundation phase."""

from typing import NoReturn

from fastapi import HTTPException

NOT_IMPLEMENTED = {501: {"description": "Domain operation is not implemented in the foundation phase"}}


def unavailable(feature: str) -> NoReturn:
    raise HTTPException(status_code=501, detail=f"{feature} is not available yet.")
