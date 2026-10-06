"""
LangGraph Node: assign_robot [Member 1]
Queries available robots and assigns one to the current task.
The robot-availability source is a swappable stub (query_available_robots)
clearly marked for later integration with the simulation module owned by
another team member.
"""

import logging
from typing import Any, Dict, List

from agents.task_planning.state import TaskPlanningState

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Robot availability stub
# ---------------------------------------------------------------------------
# ⚠️  INTEGRATION POINT — replace this function's body with a real call to
#     the simulation module (Member 3) once it exposes a robot-status API.
# ---------------------------------------------------------------------------
def query_available_robots() -> List[str]:
    """
    Return a list of currently available robot IDs.

    This is a **mock stub** returning a hard-coded fleet for standalone
    testing.  The simulation team should replace this implementation with
    a live query to the WarehouseEnvironment.get_idle_robots() endpoint.
    """
    return ["AMR-01", "AMR-02", "AMR-03"]


def assign_robot(state: TaskPlanningState) -> Dict[str, Any]:
    """
    Pick a robot from the available pool and assign it to the task.

    If `available_robots` is already populated in state (e.g., injected by
    the integration layer from live simulation data), use that list.
    Otherwise, fall back to the stub query_available_robots().

    On success → sets assigned_robot and status="assigned".
    On empty   → sets status="failed_no_robot" for downstream escalation.
    """
    state_robots = state.get("available_robots")
    robots: List[str] = state_robots if state_robots is not None else query_available_robots()

    if robots:
        raw_selected = robots[0]
        selected_id = raw_selected.get("id") if isinstance(raw_selected, dict) else str(raw_selected)
        logger.info("Assigned robot %s to task", selected_id)
        return {
            "available_robots": robots,
            "assigned_robot": selected_id,
            "assigned_robot_id": selected_id,
            "status": "assigned",
        }
    else:
        logger.warning("No robots available for assignment")
        return {
            "available_robots": [],
            "assigned_robot": None,
            "assigned_robot_id": None,
            "status": "failed_no_robot",
        }
