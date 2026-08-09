"""Resource limit enforcement for time duration and token/cost budgets."""

from datetime import datetime, timezone
from typing import Tuple
from app.core.state import AgentState


def is_budget_exceeded(state: AgentState) -> bool:
    """Check if cumulative token usage cost exceeds max budget ceiling."""
    return state.usage.total_cost_usd >= state.max_budget_usd


def is_timeout_exceeded(state: AgentState) -> bool:
    """Check if total execution duration exceeds max allowed time ceiling."""
    now = datetime.now(timezone.utc)
    elapsed = (now - state.start_time).total_seconds()
    return elapsed >= state.max_execution_seconds


def validate_state_limits(state: AgentState) -> Tuple[bool, str]:
    """Validate all runtime resource limits.
    
    Returns:
        (is_within_limits: bool, failure_reason: str)
    """
    if is_budget_exceeded(state):
        return False, f"Cost budget exceeded: ${state.usage.total_cost_usd:.4f} >= ${state.max_budget_usd:.4f}"
    
    if is_timeout_exceeded(state):
        now = datetime.now(timezone.utc)
        elapsed = (now - state.start_time).total_seconds()
        return False, f"Execution timeout exceeded: {elapsed:.1f}s >= {state.max_execution_seconds:.1f}s"
        
    return True, ""
