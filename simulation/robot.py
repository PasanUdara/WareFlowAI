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
        payload_cap_kg: float = 50.0,
        name: Optional[str] = None,
        model: str = "AMR",
        capabilities: Optional[List[str]] = None,
        enabled: bool = True
    ):
        self.robot_id = robot_id
        self.name = name or f"Warehouse Robot {robot_id.replace('AMR-', '').replace('R', '')}"
        self.model = model
        self.capabilities = capabilities if capabilities is not None else ["transport", "pallet"]
        self.enabled = enabled
        from datetime import datetime, timezone
        self.created_at = datetime.now(timezone.utc).isoformat()
        
        self.position = start_pos
        self.battery = battery
        self.payload_cap_kg = payload_cap_kg
        self.state = RobotState.IDLE
        self.waypoints: List[Tuple[int, int]] = []
        self.destination: Optional[Tuple[int, int]] = None
        self.current_task_id: Optional[str] = None
        self.speed_ms = 1.0
        self.stuck_duration = 0.0
        self.is_rerouted = False
        self.intermediate_target: Optional[Tuple[int, int]] = None
        self.final_destination: Optional[Tuple[int, int]] = None
        self.source_pos: Optional[Tuple[int, int]] = None
        self.source_name: Optional[str] = None
        self.destination_name: Optional[str] = None
        self.source_active: bool = False
        self.item: Optional[str] = None
        self.loading_duration: float = 0.0
        self.loaded: bool = False
        self.status_text: Optional[str] = None
        
    def to_telemetry(self) -> Dict[str, Any]:
        """Serialize current state into normalized telemetry dictionary."""
        pos = list(self.position) if isinstance(self.position, (list, tuple)) else [0, 0]
        x_val, y_val = pos[0] if len(pos) > 0 else 0, pos[1] if len(pos) > 1 else 0
        return {
            "robot_id": self.robot_id,
            "name": self.name,
            "model": self.model,
            "x": x_val,
            "y": y_val,
            "position": [x_val, y_val],
            "destination": list(self.destination) if self.destination else None,
            "battery": round(self.battery, 1),
            "state": self.state.value if hasattr(self.state, "value") else str(self.state),
            "speed_ms": self.speed_ms,
            "current_task": self.current_task_id,
            "current_task_id": self.current_task_id,
            "capabilities": self.capabilities,
            "enabled": self.enabled,
            "created_at": self.created_at,
            "stuck_duration": self.stuck_duration,
            "waypoints": [list(w) for w in self.waypoints],
            "waypoints_remaining": len(self.waypoints),
            "is_rerouted": getattr(self, "is_rerouted", False),
            "intermediate_target": list(self.intermediate_target) if getattr(self, "intermediate_target", None) else None,
            "final_destination": list(self.final_destination) if getattr(self, "final_destination", None) else None,
            "source_location": list(self.source_pos) if getattr(self, "source_pos", None) else None,
            "source_name": getattr(self, "source_name", None),
            "destination_name": getattr(self, "destination_name", None),
            "source_active": getattr(self, "source_active", False),
            "loaded": getattr(self, "loaded", False),
            "loading_duration": round(getattr(self, "loading_duration", 0.0), 1),
            "item": getattr(self, "item", None),
            "status_text": getattr(self, "status_text", None)
        }

    def tick(self, delta_time: float = 0.5):
        """Advance robot physics, position, and battery consumption."""
        if self.state == RobotState.MOVING:
            if self.waypoints:
                self.position = self.waypoints.pop(0)
                if self.intermediate_target and self.position == self.intermediate_target:
                    self.intermediate_target = None
                    # Reached source pickup location! Stay a few seconds to load items
                    self.state = RobotState.PICKING
                    self.loading_duration = 3.0
                    self.status_text = f"Loading {self.item or 'items'} from {self.source_name or 'source'}..."
                # Active motion battery drain (higher with payload)
                drain = (1.2 if getattr(self, "loaded", False) else 0.8) * delta_time
                self.battery = max(0.0, self.battery - drain)

            if not self.waypoints and self.state == RobotState.MOVING:
                self.state = RobotState.IDLE
                self.loaded = False
                self.source_active = False
                self.status_text = "Idle"
        elif self.state == RobotState.PICKING:
            self.battery = max(0.0, self.battery - (0.4 * delta_time))
            self.loading_duration = max(0.0, self.loading_duration - delta_time)
            secs_left = max(1, int(round(self.loading_duration)))
            self.status_text = f"Loading {self.item or 'items'} ({secs_left}s)..."
            if self.loading_duration <= 0.0:
                # Loading complete: turn source indicator off and resume travel
                self.source_active = False
                self.loaded = True
                self.state = RobotState.MOVING if self.waypoints else RobotState.IDLE
                self.status_text = (
                    f"Carrying {self.item or 'items'} → {self.destination_name or 'Station'}"
                    if self.waypoints
                    else "Idle"
                )
        elif self.state == RobotState.IDLE:
            # Standby minimal battery drain
            self.battery = max(0.0, self.battery - (0.02 * delta_time))
        elif self.state == RobotState.CHARGING:
            # Rapid charge replenishment back to 100%
            self.battery = min(100.0, self.battery + (4.0 * delta_time))
            charge_level = int(round(self.battery))
            self.status_text = f"Recharging battery ({charge_level}%)..."
            if self.battery >= 99.5:
                self.battery = 100.0
                self.state = RobotState.IDLE
                self.status_text = "Idle"
        elif self.state == RobotState.STUCK:
            self.stuck_duration += delta_time

