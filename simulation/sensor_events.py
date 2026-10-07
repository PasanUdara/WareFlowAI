"""
Fake Sensor & Anomaly Event Generator [Member 2]
Generates simulated hardware failures, path blockages, and low-battery events for testing agents.
"""

from simulation import robot
import random
from typing import Dict, Any, Optional
from .robot import Robot, RobotState


class SensorEventGenerator:
    """Injects synthetic sensor faults and telemetry anomalies."""

    def __init__(self, anomaly_probability: Optional[float] = None):
        if anomaly_probability is None:
            import os
            anomaly_probability = float(os.getenv("ANOMALY_PROBABILITY", "0.0"))
        self.anomaly_probability = anomaly_probability

    def maybe_inject_anomaly(self, robot: Robot) -> Optional[Dict[str, Any]]:
        """
        Periodically trigger a synthetic anomaly on a robot for testing.
        
        Args:
            robot: Robot instance to inject anomaly into.
            
        Returns:
            Anomaly event dict if injected, else None.
        """
        if self.anomaly_probability <= 0.0 or random.random() > self.anomaly_probability:
            return None

        if robot.battery <= 20.0:
            return self.trigger_low_battery(robot, battery_level=10.0)

        # Only inject stuck state if robot is active/moving or has waypoints/destination
        if robot.state == RobotState.MOVING or robot.destination is not None or len(robot.waypoints) > 0:
            return self.trigger_stuck(robot)

        return None


    def trigger_stuck(self, robot: Robot) -> Dict[str, Any]:
        """Force a robot into a STUCK condition."""
        robot.state = RobotState.STUCK
        robot.stuck_duration = 12.0
        return {
            "event_type": "ROBOT_STUCK",
            "robot_id": robot.robot_id,
            "position": robot.position,
            "state": robot.state.value,
            "stuck_duration": robot.stuck_duration,
            "battery": robot.battery,
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
