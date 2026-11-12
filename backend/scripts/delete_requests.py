import asyncio
import sys
from uuid import UUID

from sqlalchemy import delete

from app.core.config import Settings
from app.db.models import (
    AgentExecution,
    ConversationMessage,
    Evaluation,
    ProcurementReport,
    ProcurementRequest,
    ProductCandidate,
    WorkflowEvent,
)
from app.db.session import create_database_engine


async def main(request_ids: list[UUID]) -> None:
    engine = create_database_engine(Settings().database_url)
    try:
        async with engine.begin() as connection:
            for model in (
                ConversationMessage,
                Evaluation,
                AgentExecution,
                WorkflowEvent,
                ProcurementReport,
                ProductCandidate,
            ):
                await connection.execute(
                    delete(model).where(model.procurement_request_id.in_(request_ids))
                )
            await connection.execute(
                delete(ProcurementRequest).where(ProcurementRequest.id.in_(request_ids))
            )
    finally:
        await engine.dispose()
    print(f"Deleted {len(request_ids)} request(s).")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit("Usage: delete_requests.py REQUEST_ID [REQUEST_ID ...]")
    asyncio.run(main([UUID(value) for value in sys.argv[1:]]))
