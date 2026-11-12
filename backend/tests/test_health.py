from __future__ import annotations

from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import Settings
from app.main import create_app


class UnavailableSession:
    async def __aenter__(self) -> UnavailableSession:
        return self

    async def __aexit__(self, *args: object) -> None:
        return None

    async def execute(self, statement: object) -> None:
        raise SQLAlchemyError("private database connection detail")


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    settings = Settings(
        database_url="sqlite+aiosqlite:///:memory:",
        frontend_origin="http://localhost:3000",
    )
    application = create_app(settings)
    async with application.router.lifespan_context(application):
        async with AsyncClient(
            transport=ASGITransport(app=application),
            base_url="http://test",
        ) as test_client:
            yield test_client


async def test_health_reports_database_connection(client: AsyncClient) -> None:
    response = await client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "services": {"database": "connected"},
    }


async def test_health_has_no_cross_origin_access_for_unconfigured_origin(
    client: AsyncClient,
) -> None:
    response = await client.get(
        "/api/v1/health",
        headers={"Origin": "https://not-allowed.example"},
    )

    assert response.status_code == 200
    assert "access-control-allow-origin" not in response.headers


async def test_health_reports_database_failure_without_connection_details() -> None:
    application = create_app(
        Settings(database_url="sqlite+aiosqlite:///:memory:"),
    )
    async with application.router.lifespan_context(application):
        application.state.session_factory = UnavailableSession
        async with AsyncClient(
            transport=ASGITransport(app=application),
            base_url="http://test",
        ) as test_client:
            response = await test_client.get("/api/v1/health")

    assert response.status_code == 503
    assert response.json() == {
        "status": "degraded",
        "services": {"database": "unavailable"},
    }
    assert "private database connection detail" not in response.text
