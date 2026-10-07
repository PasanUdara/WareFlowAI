"""
Robot State Model & Telemetry [Member 2]
"""

from enum import Enum
from typing import Tuple, List, Optional, Dict, Any


class RobotState(str, Enum):
    IDLE = "IDLE"
    MOVING = "MOVING"
    PICKING = "PICKING"
    CHARGING = "CHARGING"
    STUCK = "STUCK"
    ERROR = "ERROR"


class Robot:
    """
    Autonomous Mobile Robot (AMR) entity in the simulation.
    """
    
    def __init__(
        self,
        robot_id: str,
        start_pos: Tuple[int, int] = (0, 0),
        battery: float = 100.0,
        payload_cap_kg: float = 50.0
    ):
        self.robot_id = robot_id
        self.position = start_pos
        self.battery = battery
        self.payload_cap_kg = payload_cap_kg
        self.state = RobotState.IDLE
        self.waypoints: List[Tuple[int, int]] = []
        self.destination: Optional[Tuple[int, int]] = None
        self.current_task_id: Optional[str] = None
        self.speed_ms = 1.0
        self.stuck_duration = 0.0
        
    def to_telemetry(self) -> Dict[str, Any]:
        """Serialize current state into telemetry dictionary."""
        return {
            "robot_id": self.robot_id,
            "position": self.position,
            "x": self.position[0],
            "y": self.position[1],
            "destination": self.destination,
            "battery": round(self.battery, 1),
            "state": self.state.value,
            "speed_ms": self.speed_ms,
            "current_task_id": self.current_task_id,
            "stuck_duration": self.stuck_duration,
            "waypoints_remaining": len(self.waypoints)
        }

    def tick(self, delta_time: float = 0.5):
        """Advance robot physics, position, and battery consumption."""
        if self.state == RobotState.MOVING and self.waypoints:
            self.position = self.waypoints.pop(0)
            self.battery = max(0.0, self.battery - (0.1 * delta_time))
            if not self.waypoints:
                self.state = RobotState.IDLE
        elif self.state == RobotState.CHARGING:
            self.battery = min(100.0, self.battery + (1.0 * delta_time))
            if self.battery >= 99.0:
                self.state = RobotState.IDLE
        elif self.state == RobotState.STUCK:
            self.stuck_duration += delta_time
