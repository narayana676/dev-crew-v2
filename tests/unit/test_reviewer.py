"""Unit tests for Reviewer node."""

from app.core.state import AgentState, AgentStatus, CodeFile, ReviewOutput
from app.graph.nodes import reviewer_node


def test_reviewer_node_generates_structured_review():
    """Verify Reviewer node produces ReviewOutput and updates state."""
    state = AgentState(task_description="Build a REST API")
    state.code_files["main.py"] = CodeFile(path="main.py", content="def app(): pass", language="python")

    result = reviewer_node(state)
    assert result["status"] == AgentStatus.TESTING
    assert len(result["review_notes"]) == 1

    latest_review = result["review_notes"][0]
    assert isinstance(latest_review, ReviewOutput)
    assert latest_review.passed is True
    assert latest_review.score > 0.0
    assert result["usage"].total_tokens > 0
