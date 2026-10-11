"""
Recovery Decision Engine [Member 2]
Determines the appropriate recovery action for detected robot anomalies.
"""

from typing import Dict, Any


class RecoveryEngine:
    """Evaluates anomalies and returns recovery instructions."""

    def decide_action(self, anomaly: Dict[str, Any]) -> Dict[str, Any]:
        """
        Map detected anomaly to a recovery action.

        Args:
            anomaly: Dictionary containing anomaly_type, robot_id, severity.

        Returns:
            Recovery action following the documented Exception-Handling protocol.
        """
        anomaly_type = anomaly.get("anomaly_type")
        robot_id = anomaly.get("robot_id")

        if anomaly_type == "LOW_BATTERY":
            return {
                "action_type": "RETURN_TO_CHARGER",
                "robot_id": robot_id,
                "waypoints": [],
                "notes": "Robot battery is critically low; return to charging station."
            }

        elif anomaly_type in {"ROBOT_STUCK", "PATH_BLOCKED", "OBSTACLE_DETECTED"}:
            return {
                "action_type": "REROUTE",
                "robot_id": robot_id,
                "waypoints": [],
                "notes": "Obstacle or stall detected on robot path; calculating alternate A* detour route around blocked cells."
            }

        elif anomaly_type in {"MOTOR_STALL"}:
            return {
                "action_type": "ESCALATE_TO_HUMAN",
                "robot_id": robot_id,
                "waypoints": [],
                "notes": f"Hardware alert: {anomaly_type}"
            }

        else:
            return {
                "action_type": "ESCALATE_TO_HUMAN",
                "robot_id": robot_id,
                "waypoints": [],
                "notes": f"Unknown anomaly type: {anomaly_type}"
            }