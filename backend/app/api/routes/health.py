import logging

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

logger = logging.getLogger(__name__)
router = APIRouter()


class ServiceHealth(BaseModel):
    database: str


class HealthResponse(BaseModel):
    status: str
    services: ServiceHealth


@router.get("/health", response_model=HealthResponse)
async def health(request: Request) -> JSONResponse:
    session_factory = request.app.state.session_factory

    try:
        async with session_factory() as session:
            await session.execute(text("SELECT 1"))
    except SQLAlchemyError:
        logger.warning("Health check failed: database is unavailable")
        return JSONResponse(
            status_code=503,
            content={
                "status": "degraded",
                "services": {"database": "unavailable"},
            },
        )

    return JSONResponse(
        status_code=200,
        content={
            "status": "ok",
            "services": {"database": "connected"},
        },
    )
