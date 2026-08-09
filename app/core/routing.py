"""Pure deterministic routing functions for LangGraph conditional edges."""

from typing import Literal
from app.core.limits import validate_state_limits
from app.core.state import AgentState, AgentStatus


def route_after_tester(state: AgentState) -> Literal["done", "debugger", "failed_max_retries"]:
    """Pure conditional edge router evaluated after the Tester node.
    
    Order of evaluation:
    1. Resource limits guard (budget USD / timeout seconds). If exceeded -> 'failed_max_retries'.
    2. Tests passed -> 'done'.
    3. Retry ceiling check (retry_count < max_retries). If retries left -> 'debugger'.
    4. Terminal failure ceiling reached -> 'failed_max_retries'.
    """
    within_limits, reason = validate_state_limits(state)
    if not within_limits:
        return "failed_max_retries"

    if state.tests_passed:
        return "done"

    if state.retry_count < state.max_retries:
        return "debugger"

    return "failed_max_retries"
