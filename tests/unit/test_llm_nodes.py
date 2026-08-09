"""Unit tests for Planner, Architect, and Coder nodes with LLM structured outputs."""

import pytest
from app.core.state import AgentState, AgentStatus, PlanOutput
from app.graph.nodes import architect_node, coder_node, planner_node
from app.llm.base import MockLLMProvider, OpenAIProvider, get_llm_provider


def test_llm_provider_factory():
    """Verify provider factory returns appropriate instance."""
    provider_mock = get_llm_provider("mock")
    assert isinstance(provider_mock, MockLLMProvider)

    provider_openai = get_llm_provider("openai")
    assert isinstance(provider_openai, OpenAIProvider)


def test_planner_node_structured_output():
    """Verify Planner node generates structured PlanOutput and tracks usage."""
    state = AgentState(task_description="Build a file parser")
    result = planner_node(state)

    assert result["status"] == AgentStatus.ARCHITECTING
    assert isinstance(result["plan"], PlanOutput)
    assert result["plan"].summary != ""
    assert len(result["plan"].tasks) > 0
    assert result["usage"].total_tokens > 0


def test_architect_node_structured_output():
    """Verify Architect node generates structured ArchitectureOutput."""
    state = AgentState(task_description="Build a file parser")
    # First run planner
    planner_res = planner_node(state)
    state.plan = planner_res["plan"]

    result = architect_node(state)
    assert result["status"] == AgentStatus.AWAITING_APPROVAL
    assert result["architecture"] is not None
    assert len(result["file_tree"]) > 0


def test_coder_node_structured_output():
    """Verify Coder node generates code files."""
    state = AgentState(task_description="Build a file parser")
    planner_res = planner_node(state)
    state.plan = planner_res["plan"]
    arch_res = architect_node(state)
    state.architecture = arch_res["architecture"]

    result = coder_node(state)
    assert result["status"] == AgentStatus.REVIEWING
    assert "main.py" in result["code_files"]
    assert "test_main.py" in result["code_files"]
