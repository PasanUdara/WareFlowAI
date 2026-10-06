"""
LangGraph Workflow Orchestration [Member 1]
Wires together all Task Planning nodes with conditional routing:

  START ──► parse_order ──►┬── (parsed)        ──► decompose_tasks ──► assign_robot ──►┬── (assigned)       ──► END
                           │                                                           │
                           └── (parse_failed)  ──► clarify_order   ──► END             └── (failed_no_robot)──► escalate_to_human ──► END
"""

from typing import Literal

from langgraph.graph import END, START, StateGraph

from agents.task_planning.nodes import (
    assign_robot,
    clarify_order,
    decompose_tasks,
    escalate_to_human,
    parse_order,
)
from agents.task_planning.state import TaskPlanningState


# ---------------------------------------------------------------------------
# Conditional routing functions
# ---------------------------------------------------------------------------
def route_after_parse(state: TaskPlanningState) -> Literal["decompose_tasks", "clarify_order"]:
    """Route to decompose_tasks on success, clarify_order on parse failure."""
    if state.get("status") == "parsed":
        return "decompose_tasks"
    return "clarify_order"


def route_after_assign(state: TaskPlanningState) -> Literal["__end__", "escalate_to_human"]:
    """Route to END on successful assignment, escalate otherwise."""
    if state.get("status") == "assigned":
        return END
    return "escalate_to_human"


# ---------------------------------------------------------------------------
# Graph builder
# ---------------------------------------------------------------------------
def build_task_planning_graph():
    """
    Construct and compile the Task Planning LangGraph StateGraph.

    Returns a compiled graph that can be invoked with an initial
    TaskPlanningState dict.
    """
    workflow = StateGraph(TaskPlanningState)

    # Register nodes
    workflow.add_node("parse_order", parse_order)
    workflow.add_node("decompose_tasks", decompose_tasks)
    workflow.add_node("assign_robot", assign_robot)
    workflow.add_node("escalate_to_human", escalate_to_human)
    workflow.add_node("clarify_order", clarify_order)

    # Entry point
    workflow.add_edge(START, "parse_order")

    # Conditional edge after parsing
    workflow.add_conditional_edges(
        "parse_order",
        route_after_parse,
        {
            "decompose_tasks": "decompose_tasks",
            "clarify_order": "clarify_order",
        },
    )

    # Linear edge
    workflow.add_edge("decompose_tasks", "assign_robot")

    # Conditional edge after assignment
    workflow.add_conditional_edges(
        "assign_robot",
        route_after_assign,
        {
            END: END,
            "escalate_to_human": "escalate_to_human",
        },
    )

    # Terminal edges
    workflow.add_edge("escalate_to_human", END)
    workflow.add_edge("clarify_order", END)

    return workflow.compile()
