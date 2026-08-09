"""Run execution manager service for running LangGraph graphs asynchronously."""

import asyncio
from datetime import datetime, timezone
from typing import AsyncGenerator, Dict, Optional
from uuid import uuid4

from app.core.state import AgentState, AgentStatus
from app.graph.checkpointer import get_checkpointer
from app.graph.workflow import build_dev_crew_graph


class RunManager:
    """Manages asynchronous state graph execution and SSE progress streaming."""

    def __init__(self):
        self._runs: Dict[str, AgentState] = {}
        self._listeners: Dict[str, list] = {}
        self._checkpointer = get_checkpointer(use_postgres=False)
        self._graph = build_dev_crew_graph(checkpointer=self._checkpointer)

    def create_run(self, project_id: str, task_description: str, run_id: Optional[str] = None) -> AgentState:
        """Create new execution run state and register it."""
        rid = run_id or str(uuid4())
        state = AgentState(
            run_id=rid,
            project_id=project_id,
            task_description=task_description,
            status=AgentStatus.PLANNING,
        )
        self._runs[rid] = state
        self._listeners[rid] = []
        return state

    def get_run(self, run_id: str) -> Optional[AgentState]:
        """Retrieve run state by run_id."""
        return self._runs.get(run_id)

    async def execute_run_async(self, run_id: str) -> None:
        """Execute graph state machine asynchronously step by step and notify stream listeners."""
        state = self._runs.get(run_id)
        if not state:
            return

        thread_config = {"configurable": {"thread_id": run_id}}

        # Stream node-by-node updates from LangGraph engine
        async for event in self._graph.astream(state, config=thread_config):
            for node_name, node_state in event.items():
                # Merge updated node state fields back into manager state
                if isinstance(node_state, dict):
                    for key, val in node_state.items():
                        if hasattr(state, key):
                            setattr(state, key, val)
                    state.updated_at = datetime.now(timezone.utc)
                elif isinstance(node_state, AgentState):
                    state = node_state

                # Broadcast step event to active SSE listeners
                payload = {
                    "node": node_name,
                    "status": state.status,
                    "retry_count": state.retry_count,
                    "tests_passed": state.tests_passed,
                    "updated_at": state.updated_at.isoformat(),
                }
                for queue in list(self._listeners.get(run_id, [])):
                    await queue.put(payload)

        # Notify completion
        for queue in list(self._listeners.get(run_id, [])):
            await queue.put({"node": "END", "status": state.status, "completed": True})

    async def subscribe_run_stream(self, run_id: str) -> AsyncGenerator[dict, None]:
        """Subscribe to Server-Sent Events stream for node progress updates."""
        queue: asyncio.Queue = asyncio.Queue()
        if run_id not in self._listeners:
            self._listeners[run_id] = []
        self._listeners[run_id].append(queue)

        try:
            while True:
                data = await queue.get()
                yield data
                if data.get("completed"):
                    break
        finally:
            if run_id in self._listeners and queue in self._listeners[run_id]:
                self._listeners[run_id].remove(queue)


# Global singleton instance
run_manager = RunManager()
