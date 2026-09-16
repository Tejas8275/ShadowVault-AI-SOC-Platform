"""Versioned API composition."""

from fastapi import APIRouter

from app.api.routes.health import router as health_router
from app.api.routes.auth import router as auth_router
from app.api.routes.incidents import router as incidents_router
from app.api.routes.evidence import router as evidence_router
from app.api.routes.timeline import router as timeline_router
from app.api.routes.collection import router as collection_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health_router)
api_router.include_router(auth_router)
api_router.include_router(incidents_router)
api_router.include_router(evidence_router)
api_router.include_router(timeline_router)
api_router.include_router(collection_router)
