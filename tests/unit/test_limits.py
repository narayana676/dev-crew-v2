"""Unit tests for budget, timeout, and retry limit guards."""

from datetime import datetime, timedelta, timezone
import pytest
from app.core.limits import is_budget_exceeded, is_timeout_exceeded, validate_state_limits
from app.core.routing import route_after_tester
from app.core.state import AgentState, UsageMetrics


def test_budget_limit_guard():
    """Verify cost budget ceiling detection."""
    state = AgentState(task_description="test", max_budget_usd=1.0)
    assert not is_budget_exceeded(state)

    state.usage.total_cost_usd = 0.99
    assert not is_budget_exceeded(state)

    state.usage.total_cost_usd = 1.05
    assert is_budget_exceeded(state)

    within, reason = validate_state_limits(state)
    assert not within
    assert "Cost budget exceeded" in reason


def test_timeout_limit_guard():
    """Verify time limit ceiling detection."""
    state = AgentState(task_description="test", max_execution_seconds=60.0)
    assert not is_timeout_exceeded(state)

    # Simulate past start time
    state.start_time = datetime.now(timezone.utc) - timedelta(seconds=75)
    assert is_timeout_exceeded(state)

    within, reason = validate_state_limits(state)
    assert not within
    assert "Execution timeout exceeded" in reason


def test_route_after_tester_with_resource_violations():
    """Verify router terminates immediately if budget or timeout is violated."""
    # Scenario 1: Budget exceeded despite tests passing -> failed_max_retries
    state_budget = AgentState(task_description="test", tests_passed=True, max_budget_usd=1.0)
    state_budget.usage.total_cost_usd = 1.50
    assert route_after_tester(state_budget) == "failed_max_retries"

    # Scenario 2: Timeout exceeded despite tests passing -> failed_max_retries
    state_timeout = AgentState(task_description="test", tests_passed=True, max_execution_seconds=10.0)
    state_timeout.start_time = datetime.now(timezone.utc) - timedelta(seconds=20)
    assert route_after_tester(state_timeout) == "failed_max_retries"

    # Scenario 3: Within limits and tests pass -> done
    state_ok = AgentState(task_description="test", tests_passed=True, max_budget_usd=2.0)
    assert route_after_tester(state_ok) == "done"

    # Scenario 4: Retries left within limits -> debugger
    state_retry = AgentState(task_description="test", tests_passed=False, retry_count=1, max_retries=3)
    assert route_after_tester(state_retry) == "debugger"
