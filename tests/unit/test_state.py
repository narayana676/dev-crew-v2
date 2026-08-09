"""Unit tests for AgentState Pydantic v2 schema and supporting models."""

import pytest
from pydantic import ValidationError
from app.core.state import (
    AgentState,
    AgentStatus,
    ArchitectureOutput,
    CodeFile,
    PlanOutput,
    PlanTask,
    ReviewOutput,
    TestResult,
    TestStatus,
    UsageMetrics,
)


def test_agent_status_enums():
    """Verify all required status enum values exist."""
    statuses = {s.value for s in AgentStatus}
    expected = {
        "PLANNING",
        "ARCHITECTING",
        "AWAITING_APPROVAL",
        "CODING",
        "REVIEWING",
        "TESTING",
        "DEBUGGING",
        "DONE",
        "FAILED_MAX_RETRIES",
    }
    assert expected.issubset(statuses)


def test_agent_state_defaults():
    """Verify AgentState initializes with correct defaults."""
    state = AgentState(task_description="Build a REST API")
    assert state.task_description == "Build a REST API"
    assert state.status == AgentStatus.PLANNING
    assert state.retry_count == 0
    assert state.max_retries == 3
    assert state.tests_passed is False
    assert state.plan_approved is False
    assert state.plan is None
    assert state.architecture is None
    assert isinstance(state.code_files, dict)
    assert isinstance(state.file_tree, list)
    assert isinstance(state.review_notes, list)
    assert isinstance(state.test_results, list)
    assert state.usage.total_tokens == 0
    assert state.usage.total_cost_usd == 0.0


def test_usage_metrics_cost_calculation():
    """Test token usage and cost tracking."""
    usage = UsageMetrics()
    usage.add_usage(prompt=1000, completion=500, cost_per_1k_prompt=0.0015, cost_per_1k_comp=0.002)
    assert usage.prompt_tokens == 1000
    assert usage.completion_tokens == 500
    assert usage.total_tokens == 1500
    assert usage.total_cost_usd == pytest.approx(0.0025)


def test_code_file_and_plan_structures():
    """Test nested model instantiation."""
    code = CodeFile(path="main.py", content="print('hello')", language="python")
    assert code.path == "main.py"

    task = PlanTask(id="task-1", title="Setup DB", description="Create SQLAlchemy models")
    plan = PlanOutput(summary="Build system", architecture_overview="Modular", tasks=[task])
    assert len(plan.tasks) == 1
    assert plan.tasks[0].id == "task-1"


def test_agent_state_status_update():
    """Test updating state status updates timestamp."""
    state = AgentState(task_description="Test status update")
    t1 = state.updated_at
    state.update_status(AgentStatus.CODING)
    assert state.status == AgentStatus.CODING
    assert state.updated_at >= t1


def test_agent_state_strict_validation():
    """Verify Pydantic raises validation error for invalid types."""
    with pytest.raises(ValidationError):
        AgentState(task_description=12345)  # Invalid type if strict, or valid depending on pydantic coerced mode
