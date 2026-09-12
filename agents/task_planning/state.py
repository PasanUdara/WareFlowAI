"""
State definition for Task Planning Agent LangGraph workflow [Member 1]
"""

from typing import TypedDict, Optional, List, Dict, Any


class SubTask(TypedDict):
    """Represents a single decomposed subtask."""
    subtask_id: str
    task_type: str  # e.g., "PICK", "TRANSPORT", "DELIVER"
    sku: str
    quantity: int
    source_location: str
    destination_location: str
    status: str  # "PENDING", "IN_PROGRESS", "COMPLETED"


class TaskPlanningState(TypedDict):
    """
    TypedDict state schema passed between nodes in the Task Planning LangGraph.
    
    Fields:
        order_raw: Raw natural language order text from user/ERP.
        parsed_order: Structured representation of the order.
        subtasks: List of decomposed atomic warehouse subtasks.
        assigned_robot_id: ID of the allocated AMR (None if unassigned).
        available_robots: Cached list of available robots retrieved during planning.
        requires_escalation: Boolean flag triggering routing to human supervisor.
        escalation_reason: Reason for escalation when no robot qualifies.
        status: Overall planning status ("INITIALIZED", "PARSED", "DECOMPOSED", "ASSIGNED", "ESCALATED", "FAILED").
        error_message: Optional error details.
    """
    order_raw: str
    parsed_order: Optional[Dict[str, Any]]
    subtasks: List[SubTask]
    assigned_robot_id: Optional[str]
    available_robots: List[Dict[str, Any]]
    requires_escalation: bool
    escalation_reason: Optional[str]
    status: str
    error_message: Optional[str]
