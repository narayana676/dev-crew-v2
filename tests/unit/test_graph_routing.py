"""Unit tests for LangGraph state machine skeleton and deterministic routing logic."""

import pytest
from app.core.routing import route_after_tester
from app.core.state import AgentState, AgentStatus
from app.graph.workflow import build_dev_crew_graph


def test_router_after_tester_logic():
    """Test router function directly with mock states."""
    # State 1: Tests passed -> done
    state_pass = AgentState(task_description="test", tests_passed=True)
    assert route_after_tester(state_pass) == "done"

    # State 2: Tests failed, retries available -> debugger
    state_retry = AgentState(task_description="test", tests_passed=False, retry_count=1, max_retries=3)
    assert route_after_tester(state_retry) == "debugger"

    # State 3: Tests failed, max retries reached -> failed_max_retries
    state_fail = AgentState(task_description="test", tests_passed=False, retry_count=3, max_retries=3)
    assert route_after_tester(state_fail) == "failed_max_retries"


def test_graph_compilation():
    """Verify graph compiles without errors."""
    graph = build_dev_crew_graph()
    assert graph is not None


def test_full_graph_execution_success_path():
    """Run state machine through full success path."""
    graph = build_dev_crew_graph()
    initial_state = AgentState(task_description="Create a simple calculator")
    
    # Execute graph
    final_state_dict = graph.invoke(initial_state)
    
    # Assert final status and artifacts
    assert final_state_dict["status"] == AgentStatus.DONE
    assert final_state_dict["tests_passed"] is True
    assert final_state_dict["plan"] is not None
    assert final_state_dict["architecture"] is not None
    assert final_state_dict["plan_approved"] is True
    assert "main.py" in final_state_dict["code_files"]


def test_graph_execution_retry_and_terminal_fail():
    """Simulate test failure loop that hits max retries terminal state."""
    # Customize coder/tester node response by monkeypatching tester_node or setting state
    import app.graph.workflow as workflow_module
    
    original_tester = workflow_module.tester_node

    def failing_tester_node(state: AgentState) -> dict:
        result = original_tester(state)
        result["tests_passed"] = False
        return result

    workflow_module.tester_node = failing_tester_node
    
    try:
        graph = workflow_module.build_dev_crew_graph()
        initial_state = AgentState(task_description="Fail test task", max_retries=2)
        final_state_dict = graph.invoke(initial_state)

        assert final_state_dict["status"] == AgentStatus.FAILED_MAX_RETRIES
        assert final_state_dict["tests_passed"] is False
        assert final_state_dict["retry_count"] == 2
    finally:
        workflow_module.tester_node = original_tester
