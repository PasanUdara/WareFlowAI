"""
Warehouse Simulation Environment [Member 2]
Coordinates the 2D grid, AMR fleet lifecycle, and telemetry tick loop.
"""

from typing import Dict, List, Any
from .grid import WarehouseGrid
from .robot import Robot
from .sensor_events import SensorEventGenerator


class WarehouseEnvironment:
    """Discrete-time warehouse simulation runtime."""

    def __init__(self, width: int = 20, height: int = 15, num_robots: int = 4):
        self.grid = WarehouseGrid(width=width, height=height)
        self.robots: Dict[str, Robot] = {}
        self.sensor_generator = SensorEventGenerator()
        self._init_fleet(num_robots)
        
    def _init_fleet(self, num_robots: int):
        """Spawns AMRs at initial charging stations."""
        charging_coords = list(self.grid.charging_stations)
        for i in range(num_robots):
            robot_id = f"R{i + 1}"
            start_pos = charging_coords[i % len(charging_coords)]
            self.robots[robot_id] = Robot(
                robot_id=robot_id,
                start_pos=start_pos,
                battery=100.0,
                payload_cap_kg=50.0
            )

    def get_fleet_telemetry(self) -> List[Dict[str, Any]]:
        """Return array of all robot telemetry packets."""
        return [robot.to_telemetry() for robot in self.robots.values()]

    def tick(self, delta_time: float = 0.5) -> List[Dict[str, Any]]:
        """
        Advance one simulation time step.
        
        Returns:
            List of any anomaly events triggered during this tick.
        """
        anomalies = []
        for robot in self.robots.values():
            robot.tick(delta_time)
            anomaly = self.sensor_generator.maybe_inject_anomaly(robot)
            if anomaly:
                anomalies.append(anomaly)
        return anomalies
