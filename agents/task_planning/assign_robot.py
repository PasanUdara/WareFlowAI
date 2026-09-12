"""
LangGraph Node: assign_robot [Member 1]
Checks simulated fleet availability and assigns the optimal robot to decomposed subtasks.
If no robot is available (or all have low battery/are busy), flags requires_escalation = True.
"""

from typing import Dict, Any, List
from .state import TaskPlanningState


def assign_robot(state: TaskPlanningState) -> Dict[str, Any]:
    """
    Evaluate available warehouse AMRs and assign the most suitable robot.
    
    Args:
        state: Current TaskPlanningState containing subtasks and available_robots.
        
    Returns:
        State dictionary update with 'assigned_robot_id', 'requires_escalation',
        and 'escalation_reason' if no robot is available.
    """
    available_robots: List[Dict[str, Any]] = state.get("available_robots", [])
    
    # TODO: [Member 1] Implement multi-criteria allocation algorithm:
    # 1. Check battery >= 20%
    # 2. Check robot state == IDLE
    # 3. Check payload capacity >= subtask weight
    # 4. Minimize distance to source location
    
    # Placeholder: find first IDLE robot with sufficient battery
    selected_robot_id = None
    for robot in available_robots:
        if robot.get("status") == "IDLE" and robot.get("battery", 0) >= 20:
            selected_robot_id = robot.get("id")
            break
            
    if selected_robot_id:
        return {
            "assigned_robot_id": selected_robot_id,
            "requires_escalation": False,
            "escalation_reason": None,
            "status": "ASSIGNED"
        }
    else:
        return {
            "assigned_robot_id": None,
            "requires_escalation": True,
            "escalation_reason": "No available idle robots with sufficient battery (>20%) found in fleet.",
            "status": "ESCALATION_REQUIRED"
        }
