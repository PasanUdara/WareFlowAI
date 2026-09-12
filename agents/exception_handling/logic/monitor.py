"""
Telemetry Monitor [Member 2]
Inspects simulated robot sensor events to detect anomalies like stuck wheels or critical battery.
"""

from typing import Dict, Any, Optional


class TelemetryMonitor:
    """Monitors telemetry feeds for anomaly thresholds."""

    BATTERY_CRITICAL_THRESHOLD = 15.0
    STALL_TIMEOUT_SECONDS = 10.0

    def check_for_anomaly(self, telemetry: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Evaluate telemetry for threshold breaches.
        
        Args:
            telemetry: Dictionary containing 'robot_id', 'battery', 'state', 'stuck_duration', etc.
            
        Returns:
            Anomaly dictionary if detected, else None.
        """
        robot_id = telemetry.get("robot_id", "UNKNOWN")
        battery = telemetry.get("battery", 100.0)
        state = telemetry.get("state", "IDLE")
        stuck_duration = telemetry.get("stuck_duration", 0.0)
        
        # Check critical battery
        if battery < self.BATTERY_CRITICAL_THRESHOLD:
            return {
                "anomaly_type": "LOW_BATTERY",
                "robot_id": robot_id,
                "battery": battery,
                "severity": "CRITICAL"
            }
            
        # Check if robot is stuck
        if state == "STUCK" or stuck_duration > self.STALL_TIMEOUT_SECONDS:
            return {
                "anomaly_type": "ROBOT_STUCK",
                "robot_id": robot_id,
                "position": telemetry.get("position", (0, 0)),
                "severity": "HIGH"
            }
            
        return None
