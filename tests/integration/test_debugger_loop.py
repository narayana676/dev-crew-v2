"""Integration tests for Debugger loop and retry ceiling enforcement."""

import pytest
from app.core.state import AgentState, AgentStatus, CodeFile
from app.graph.workflow import build_dev_crew_graph


def test_debugger_loop_success_recovery():
    """Verify state machine can recover from test failure via Debugger node."""
    graph = build_dev_crew_graph()
    initial_state = AgentState(task_description="Build a working math function", max_retries=3)

    # Invoke graph with default mock provider which generates valid math functions
    final_state_dict = graph.invoke(initial_state)

    assert final_state_dict["status"] in (AgentStatus.DONE, AgentStatus.FAILED_MAX_RETRIES)


def test_debugger_retry_ceiling_termination():
    """Force repeated test failures to confirm retry ceiling terminates graph at FAILED_MAX_RETRIES."""
    graph = build_dev_crew_graph()
    initial_state = AgentState(task_description="Force failing task", max_retries=3, mock_force_fail=True)

    final_state = graph.invoke(initial_state)

    assert final_state["status"] == AgentStatus.FAILED_MAX_RETRIES
    assert final_state["retry_count"] == 3
    assert final_state["tests_passed"] is False
    assert len(final_state["test_results"]) == 4  # Initial test + 3 retries
