"""LangGraph workflow definition for Dev Crew multi-agent state machine."""

from typing import Literal
from langgraph.graph import END, START, StateGraph
from app.core.routing import route_after_tester
from app.core.state import AgentState
from app.graph.nodes import (
    architect_node,
    approval_stub_node,
    coder_node,
    debugger_node,
    done_node,
    failed_max_retries_node,
    planner_node,
    reviewer_node,
    tester_node,
)


def build_dev_crew_graph(checkpointer=None, interrupt_approval: bool = False):
    """Build and compile the multi-agent LangGraph workflow."""
    workflow = StateGraph(AgentState)

    # Add agent nodes
    workflow.add_node("planner", planner_node)
    workflow.add_node("architect", architect_node)
    workflow.add_node("approval", approval_stub_node)
    workflow.add_node("coder", coder_node)
    workflow.add_node("reviewer", reviewer_node)
    workflow.add_node("tester", tester_node)
    workflow.add_node("debugger", debugger_node)
    workflow.add_node("done", done_node)
    workflow.add_node("failed_max_retries", failed_max_retries_node)

    # Wire direct edges
    workflow.add_edge(START, "planner")
    workflow.add_edge("planner", "architect")
    workflow.add_edge("architect", "approval")
    workflow.add_edge("approval", "coder")
    workflow.add_edge("coder", "reviewer")
    workflow.add_edge("reviewer", "tester")

    # Wire conditional router after tester node
    workflow.add_conditional_edges(
        "tester",
        route_after_tester,
        {
            "done": "done",
            "debugger": "debugger",
            "failed_max_retries": "failed_max_retries",
        },
    )

    # Debugger loops back to Coder
    workflow.add_edge("debugger", "coder")

    # Terminal nodes lead to END
    workflow.add_edge("done", END)
    workflow.add_edge("failed_max_retries", END)

    interrupt_before = ["coder"] if interrupt_approval else None
    return workflow.compile(checkpointer=checkpointer, interrupt_before=interrupt_before)
