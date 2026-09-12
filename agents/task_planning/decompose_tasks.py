"""
LangGraph Node: decompose_tasks [Member 1]
Breaks down a parsed order into a sequence of atomic warehouse subtasks (PICK, TRANSPORT, DELIVER).
"""

from typing import Dict, Any, List
from .state import TaskPlanningState, SubTask


def decompose_tasks(state: TaskPlanningState) -> Dict[str, Any]:
    """
    Decompose parsed order items into actionable robot subtasks.
    
    Args:
        state: Current TaskPlanningState containing parsed_order.
        
    Returns:
        State dictionary update containing 'subtasks' and updated 'status'.
    """
    parsed_order = state.get("parsed_order") or {}
    items = parsed_order.get("items", [])
    
    subtasks: List[SubTask] = []
    
    # TODO: [Member 1] Implement smart decomposition logic handling multi-item batches,
    # capacity constraints, and staging locations.
    
    for idx, item in enumerate(items, start=1):
        subtasks.append({
            "subtask_id": f"SUB-{idx:03d}-PICK",
            "task_type": "PICK",
            "sku": item.get("sku", "UNKNOWN"),
            "quantity": item.get("quantity", 1),
            "source_location": item.get("source", "Aisle-1"),
            "destination_location": item.get("source", "Aisle-1"),
            "status": "PENDING"
        })
        subtasks.append({
            "subtask_id": f"SUB-{idx:03d}-DELIVER",
            "task_type": "DELIVER",
            "sku": item.get("sku", "UNKNOWN"),
            "quantity": item.get("quantity", 1),
            "source_location": item.get("source", "Aisle-1"),
            "destination_location": item.get("destination", "Station-1"),
            "status": "PENDING"
        })
        
    return {
        "subtasks": subtasks,
        "status": "DECOMPOSED"
    }
