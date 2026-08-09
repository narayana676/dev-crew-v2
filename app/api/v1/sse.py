"""Server-Sent Events (SSE) streaming endpoint for live graph progress."""

import json
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse
from app.services.run_manager import run_manager

router = APIRouter(prefix="/runs", tags=["stream"])


@router.get("/{run_id}/stream", response_class=StreamingResponse)
async def stream_run_progress(run_id: str):
    """Stream live node-by-node state transitions via Server-Sent Events (SSE)."""
    state = run_manager.get_run(run_id)
    if not state:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Run '{run_id}' not found.")

    async def event_generator():
        # Stream events produced during execution
        async for event in run_manager.subscribe_run_stream(run_id):
            yield f"data: {json.dumps(event)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
