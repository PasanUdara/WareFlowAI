"""
LangGraph Node: assign_robot [Member 1]
Queries available robots and assigns one to the current task.
The robot-availability source is a swappable stub (query_available_robots)
clearly marked for later integration with the simulation module owned by
another team member.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

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


def _resolve_source_coords(source_name: Optional[str]) -> Optional[Tuple[int, int]]:
    """Resolve a warehouse location string to grid coordinates."""
    if not source_name or not isinstance(source_name, str):
        return None
    try:
        from simulation.environment import LOCATION_MAP
        clean = source_name.strip().lower().rstrip(".").rstrip(",")
        if clean in LOCATION_MAP:
            return LOCATION_MAP[clean]
        # Match station and shelf keywords
        if "station" in clean and "3" in clean:
            return (17, 12)
        if "station" in clean and "2" in clean:
            return (16, 12)
        if "station" in clean and "1" in clean:
            return (15, 12)
        if "packing" in clean:
            return (16, 12)
        if "shelf" in clean and "a" in clean:
            return (3, 3)
        if "shelf" in clean and "b" in clean:
            return (8, 3)
        if "shelf" in clean and "c" in clean:
            return (11, 3)
        if "shelf" in clean and "d" in clean:
            return (14, 3)
        if "receiving" in clean:
            return (2, 1)
        if "charging" in clean:
            return (2, 13)
    except Exception as e:
        logger.debug("Could not resolve location coordinates: %s", e)
    return None


def assign_robot(state: TaskPlanningState) -> Dict[str, Any]:
    """
    Pick a robot from the available pool and assign it to the task.

    Before assigning work, searches where all robots are located at the moment,
    calculates Manhattan distance to the pickup source location, filters out
    robots with low battery (<= 20%), and prioritizes the closest robot.

    If `available_robots` is already populated in state (e.g., injected by
    the integration layer from live simulation data), use that list.
    Otherwise, fall back to the stub query_available_robots().

    On success → sets assigned_robot and status="assigned".
    On empty   → sets status="failed_no_robot" for downstream escalation.
    """
    state_robots = state.get("available_robots")
    robots: List[Any] = state_robots if state_robots is not None else query_available_robots()

    if not robots:
        logger.warning("No robots available for assignment")
        return {
            "available_robots": [],
            "assigned_robot": None,
            "assigned_robot_id": None,
            "status": "failed_no_robot",
        }

    parsed_order = state.get("parsed_order") or {}
    source_name = parsed_order.get("source")
    source_pos = _resolve_source_coords(source_name)

    # Check if robots are rich telemetry dictionaries
    candidate_dicts = [r for r in robots if isinstance(r, dict)]

    if candidate_dicts:
        # Prioritize robots with healthy battery (> 20.0%) and not in error
        healthy_candidates = [
            r for r in candidate_dicts
            if float(r.get("battery", 100.0)) > 20.0
            and str(r.get("status", "")).lower() not in ("error", "stuck")
        ]
        pool = healthy_candidates if healthy_candidates else candidate_dicts

        if source_pos:
            def _robot_sort_key(r: Dict[str, Any]):
                pos = r.get("position")
                if pos and isinstance(pos, (list, tuple)) and len(pos) == 2:
                    dist = abs(pos[0] - source_pos[0]) + abs(pos[1] - source_pos[1])
                else:
                    dist = 999
                # Nearest distance first, higher battery percentage as tie-breaker
                return (dist, -float(r.get("battery", 0.0)))

            sorted_candidates = sorted(pool, key=_robot_sort_key)
            best_robot = sorted_candidates[0]
            selected_id = str(best_robot.get("id") or best_robot.get("robot_id"))
            best_pos = best_robot.get("position")
            best_dist = (abs(best_pos[0] - source_pos[0]) + abs(best_pos[1] - source_pos[1])) if best_pos else "N/A"
            logger.info(
                "Closest robot search: assigned %s at %s (distance=%s to source '%s' at %s, battery=%.1f%%)",
                selected_id, best_pos, best_dist, source_name, source_pos, float(best_robot.get("battery", 100.0))
            )
        else:
            # Fallback if source position unknown: sort by highest battery
            sorted_candidates = sorted(pool, key=lambda r: -float(r.get("battery", 0.0)))
            best_robot = sorted_candidates[0]
            selected_id = str(best_robot.get("id") or best_robot.get("robot_id"))
            logger.info(
                "Assigned robot %s (highest battery %.1f%%)",
                selected_id, float(best_robot.get("battery", 100.0))
            )

        return {
            "available_robots": robots,
            "assigned_robot": selected_id,
            "assigned_robot_id": selected_id,
            "status": "assigned",
        }

    # Fallback for simple list of string IDs (mock stubs and unit test compatibility)
    raw_selected = robots[0]
    selected_id = raw_selected.get("id") if isinstance(raw_selected, dict) else str(raw_selected)
    logger.info("Assigned robot %s to task", selected_id)
    return {
        "available_robots": robots,
        "assigned_robot": selected_id,
        "assigned_robot_id": selected_id,
        "status": "assigned",
    }
