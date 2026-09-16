"""ASGI entry point: uvicorn app.main:app --reload."""

from contextlib import asynccontextmanager
import asyncio
from threading import BoundedSemaphore

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError

from app.api.router import api_router
from app.api.routes.investigation import router as investigation_router
from app.api.routes.investigation_timeline import router as timeline_router
from app.api.routes.investigation_retrieval import router as retrieval_router
from app.api.routes.investigation_incidents import router as incidents_router
from app.api.routes.investigation_indicators import router as indicators_router
from app.core.config import Settings
from app.core.limits import CollectionBodyLimit
from app.core.privacy import ResponsePrivacy, validation_failure
from app.db.session import build_engine, build_session_factory
from app.services.ai_model import BriefingProvider
from app.services.ai_adapter import CommandProvider
from app.services.ai_usage import UsageControl


def create_app(settings: Settings | None = None, *, ai_provider: BriefingProvider | None = None) -> FastAPI:
    settings = settings or Settings()
    if ai_provider is None and settings.ai_enabled and settings.ai_adapter_script is not None:
        ai_provider = CommandProvider(settings.ai_adapter_script, settings.ai_provider_api_key)

    @asynccontextmanager
    async def lifespan(application: FastAPI):
        engine = build_engine(settings)
        application.state.session_factory = build_session_factory(engine)
        application.state.upload_slots = asyncio.Semaphore(settings.max_concurrent_uploads)
        application.state.retrieval_slots = BoundedSemaphore(settings.max_concurrent_retrievals)
        application.state.ai_slots = BoundedSemaphore(1)
        application.state.ai_usage = UsageControl(settings.ai_min_interval_seconds,
            settings.ai_max_per_minute, settings.ai_max_attempts)
        try:
            yield
        finally:
            engine.dispose()

    application = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        lifespan=lifespan,
        docs_url=None if settings.environment == "production" else "/docs",
        redoc_url=None if settings.environment == "production" else "/redoc",
        openapi_url=None if settings.environment == "production" else "/openapi.json",
    )
    application.add_middleware(CollectionBodyLimit, max_upload_bytes=settings.max_upload_bytes)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        allow_headers=["Authorization", "Content-Type", "X-Evidence-SHA256", "X-Evidence-Size", "X-Collected-At"],
    )
    application.state.settings = settings
    application.add_middleware(ResponsePrivacy)
    application.add_exception_handler(RequestValidationError, validation_failure)
    application.state.ai_provider = ai_provider
    application.include_router(api_router)
    application.include_router(investigation_router)
    application.include_router(timeline_router)
    application.include_router(retrieval_router)
    application.include_router(incidents_router)
    application.include_router(indicators_router)

    @application.get("/health", tags=["health"])
    def liveness() -> dict[str, str]:
        return {"status": "ok"}

    return application


app = create_app()
