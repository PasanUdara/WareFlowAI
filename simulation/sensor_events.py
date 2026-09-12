"""
Fake Sensor & Anomaly Event Generator [Member 2]
Generates simulated hardware failures, path blockages, and low-battery events for testing agents.
"""

import random
from typing import Dict, Any, Optional
from .robot import Robot, RobotState


class SensorEventGenerator:
    """Injects synthetic sensor faults and telemetry anomalies."""

    def __init__(self, anomaly_probability: float = 0.05):
        self.anomaly_probability = anomaly_probability

    def maybe_inject_anomaly(self, robot: Robot) -> Optional[Dict[str, Any]]:
        """
        Periodically trigger a synthetic anomaly on a robot for testing.
        
        Args:
            robot: Robot instance to inject anomaly into.
            
        Returns:
            Anomaly event dict if injected, else None.
        """
        # Manual injection helper or probabilistic trigger
        # TODO: [Member 2] Add controllable triggers via API / dashboard buttons
        return None

    def trigger_stuck(self, robot: Robot) -> Dict[str, Any]:
        """Force a robot into a STUCK condition."""
        robot.state = RobotState.STUCK
        robot.stuck_duration = 12.0
        return {
            "event_type": "ROBOT_STUCK",
            "robot_id": robot.robot_id,
            "position": robot.position,
            "severity": "HIGH"
        }

    def trigger_low_battery(self, robot: Robot, battery_level: float = 10.0) -> Dict[str, Any]:
        """Force a robot to critically low battery."""
        robot.battery = battery_level
        return {
            "event_type": "LOW_BATTERY",
            "robot_id": robot.robot_id,
            "battery": battery_level,
            "severity": "CRITICAL"
        }
