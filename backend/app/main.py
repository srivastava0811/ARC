import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.events import router as events_router
from app.api.routes.health import router as health_router
from app.api.routes.requests import router as requests_router
from app.core.config import Settings, get_settings
from app.db.session import create_database_engine, create_session_factory


def create_app(settings: Settings | None = None) -> FastAPI:
    app_settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        logging.basicConfig(
            level=app_settings.log_level,
            format="%(asctime)s %(levelname)s %(name)s %(message)s",
        )
        engine = create_database_engine(app_settings.database_url)
        app.state.engine = engine
        app.state.session_factory = create_session_factory(engine)
        try:
            yield
        finally:
            await engine.dispose()

    application = FastAPI(
        title="ARC API",
        description="API for the Autonomous Resource Coordinator.",
        version="0.1.0",
        lifespan=lifespan,
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=[app_settings.frontend_origin],
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["Accept", "Content-Type"],
    )
    application.include_router(health_router, prefix="/api/v1")
    application.include_router(requests_router, prefix="/api/v1")
    application.include_router(events_router, prefix="/api/v1")
    return application


app = create_app()
