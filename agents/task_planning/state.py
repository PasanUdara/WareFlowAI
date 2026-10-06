"""
State Schema for Task Planning Agent [Member 1]
TypedDict definition shared across all LangGraph nodes.
"""

from typing import TypedDict, Optional, List, Dict, Any


class TaskPlanningState(TypedDict):
    """
    TypedDict state schema passed between nodes in the Task Planning LangGraph.

    Fields:
        order_text: Raw natural-language warehouse order from user / ERP system.
        parsed_order: Structured dict with keys {item, quantity, source, destination}.
        subtasks: Ordered list of atomic robot actions, each a dict with
                  keys like {step, action, target/item/qty}.
        available_robots: List of robot identifiers currently known to be available.
        assigned_robot: The ID of the robot selected for this task (None until assigned).
        status: Lifecycle tracker — one of:
                "pending", "parsed", "decomposed", "assigned",
                "escalated", "parse_failed", "needs_clarification",
                "failed_no_robot".
    """
    order_text: str
    parsed_order: Optional[Dict[str, Any]]
    subtasks: Optional[List[Dict[str, Any]]]
    available_robots: Optional[List[str]]
    assigned_robot: Optional[str]
    status: str
