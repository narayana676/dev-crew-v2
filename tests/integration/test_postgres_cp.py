"""Integration tests for state machine checkpointing and state persistence."""

import pytest
from langgraph.checkpoint.memory import MemorySaver
from app.core.state import AgentState, AgentStatus
from app.graph.checkpointer import get_checkpointer
from app.graph.workflow import build_dev_crew_graph


def test_checkpointer_factory():
    """Verify checkpointer factory returns valid checkpointer saver."""
    cp = get_checkpointer(use_postgres=False)
    assert isinstance(cp, MemorySaver)


def test_checkpointed_graph_execution_and_state_recovery():
    """Run state machine with checkpointer and verify state inspection by thread config."""
    checkpointer = MemorySaver()
    graph = build_dev_crew_graph(checkpointer=checkpointer)

    initial_state = AgentState(task_description="Build a persistant task")
    thread_config = {"configurable": {"thread_id": initial_state.run_id}}

    # Invoke compiled graph with thread configuration
    final_state = graph.invoke(initial_state, config=thread_config)
    assert final_state["status"] == AgentStatus.DONE

    # Inspect state snapshot from checkpointer by thread_id
    snapshot = graph.get_state(thread_config)
    assert snapshot is not None
    assert snapshot.values["run_id"] == initial_state.run_id
    assert snapshot.values["status"] == AgentStatus.DONE
    assert "main.py" in snapshot.values["code_files"]
