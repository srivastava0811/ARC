import asyncio
import json
from collections.abc import AsyncIterator
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import select

from app.db.models import ProcurementRequest, WorkflowEvent

router = APIRouter(prefix="/requests", tags=["events"])


@router.get("/{request_id}/events")
async def stream_events(
    request_id: UUID,
    request: Request,
    after: int = Query(default=0, ge=0),
) -> StreamingResponse:
    session_factory = request.app.state.session_factory
    async with session_factory() as session:
        if await session.get(ProcurementRequest, request_id) is None:
            raise HTTPException(status_code=404, detail="Procurement request not found")

    async def events() -> AsyncIterator[str]:
        last_event_id = request.headers.get("last-event-id")
        sequence = (
            max(after, int(last_event_id)) if last_event_id and last_event_id.isdigit() else after
        )
        while True:
            async with session_factory() as session:
                rows = (
                    await session.scalars(
                        select(WorkflowEvent)
                        .where(
                            WorkflowEvent.procurement_request_id == request_id,
                            WorkflowEvent.sequence_number > sequence,
                        )
                        .order_by(WorkflowEvent.sequence_number)
                    )
                ).all()
            for row in rows:
                sequence = row.sequence_number
                payload = {
                    "sequence": row.sequence_number,
                    "type": row.event_type,
                    "payload": row.payload,
                    "created_at": row.created_at.isoformat(),
                }
                yield f"id: {sequence}\nevent: {row.event_type}\ndata: {json.dumps(payload)}\n\n"
            if await request.is_disconnected():
                return
            yield ": keepalive\n\n"
            await asyncio.sleep(0.5)

    return StreamingResponse(events(), media_type="text/event-stream")
