import asyncio
import sys
from uuid import UUID

from sqlalchemy import select

from app.core.config import Settings
from app.db.models import AgentExecution
from app.db.session import create_database_engine, create_session_factory


async def main(request_id: UUID) -> None:
    engine = create_database_engine(Settings().database_url)
    session_factory = create_session_factory(engine)
    try:
        async with session_factory() as session:
            executions = (
                await session.scalars(
                    select(AgentExecution)
                    .where(AgentExecution.procurement_request_id == request_id)
                    .order_by(AgentExecution.started_at)
                )
            ).all()
            for execution in executions:
                print(
                    f"{execution.agent_name}: {execution.status} "
                    f"({execution.model_name})"
                )
    finally:
        await engine.dispose()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: inspect_agent_executions.py REQUEST_ID")
    asyncio.run(main(UUID(sys.argv[1])))
