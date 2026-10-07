"""
Telemetry Monitor [Member 2]
Inspects robot telemetry and detects anomalies such as
critical battery, robot stuck, blocked path, or motor stall.
"""

from typing import Dict, Any, Optional


class TelemetryMonitor:
    """Monitors telemetry feeds for anomaly thresholds."""

    BATTERY_CRITICAL_THRESHOLD = 15.0
    STALL_TIMEOUT_SECONDS = 10.0

    def check_for_anomaly(self, telemetry: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Evaluate telemetry for anomaly conditions.

        Supports both the documented telemetry contract and
        the current simulation field names.

        Documented fields:
            robot_id
            event_type
            current_position
            battery_level
            severity

        Current simulation fields:
            robot_id
            position
            battery
            state
            stuck_duration
        """

        robot_id = telemetry.get("robot_id", "UNKNOWN")

        # Support documented field name and current simulation field name.
        battery = telemetry.get(
            "battery_level",
            telemetry.get("battery", 100.0)
        )

        current_position = telemetry.get(
            "current_position",
            telemetry.get("position", (0, 0))
        )

        event_type = telemetry.get("event_type")
        state = telemetry.get("state", "IDLE")
        stuck_duration = telemetry.get("stuck_duration", 0.0)

        # Critical battery
        if battery < self.BATTERY_CRITICAL_THRESHOLD:
            return {
                "anomaly_type": "LOW_BATTERY",
                "robot_id": robot_id,
                "battery": battery,
                "position": current_position,
                "severity": "CRITICAL"
            }

        # Robot stuck
        if event_type == "ROBOT_STUCK" or state == "STUCK" or stuck_duration > self.STALL_TIMEOUT_SECONDS:
            return {
                "anomaly_type": "ROBOT_STUCK",
                "robot_id": robot_id,
                "position": current_position,
                "severity": telemetry.get("severity", "HIGH")
            }

        # Path blocked
        if event_type == "PATH_BLOCKED":
            return {
                "anomaly_type": "PATH_BLOCKED",
                "robot_id": robot_id,
                "position": current_position,
                "severity": telemetry.get("severity", "HIGH")
            }

        # Motor stall
        if event_type == "MOTOR_STALL":
            return {
                "anomaly_type": "MOTOR_STALL",
                "robot_id": robot_id,
                "position": current_position,
                "severity": telemetry.get("severity", "CRITICAL")
            }

        return None