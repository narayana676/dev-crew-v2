"""Integration test for Server-Sent Events (SSE) progress streaming endpoint."""

import asyncio
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.run_manager import run_manager

client = TestClient(app)


def test_sse_stream_endpoint_404():
    """Verify 404 error when streaming non-existent run_id."""
    res = client.get("/api/v1/runs/non-existent-run/stream")
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_sse_stream_events():
    """Verify SSE stream delivers node execution events."""
    state = run_manager.create_run(project_id="proj-sse", task_description="SSE Task")

    # Start background task execution
    task = asyncio.create_task(run_manager.execute_run_async(state.run_id))

    events = []
    async for event in run_manager.subscribe_run_stream(state.run_id):
        events.append(event)

    await task

    assert len(events) > 0
    # Check that events contain node transition info
    nodes_executed = [e["node"] for e in events if "node" in e]
    assert "planner" in nodes_executed
    assert "coder" in nodes_executed
    assert "END" in nodes_executed
