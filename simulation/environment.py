"""
Warehouse Simulation Environment [Member 2]
Coordinates the 2D grid, AMR fleet lifecycle, and telemetry tick loop.
"""
import logging
from agents.exception_handling.logic.rerouter import Rerouter
from typing import Dict, List, Any, Optional
from .grid import WarehouseGrid
from .robot import Robot, RobotState
from .sensor_events import SensorEventGenerator

logger = logging.getLogger(__name__)


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
    def reroute_robot(
        self,
        robot_id: str,
        goal: tuple[int, int]
    ) -> List[tuple[int, int]]:
        """
        Calculate and apply an alternate A* route for a robot.

        Args:
            robot_id: ID of the robot that needs rerouting.
            goal: Intended destination on the warehouse grid.

        Returns:
            Calculated waypoint path. Returns an empty list if
            the robot does not exist or no valid path is available.
        """
        robot = self.robots.get(robot_id)

        if robot is None:
            return []

        rerouter = Rerouter()

        path = rerouter.calculate_detour(
            start=robot.position,
            goal=goal,
            blocked_cells=self.grid.blocked_cells,
            grid_bounds=(self.grid.width, self.grid.height)
        )

        if not path:
            return []

        # Current position is already occupied by the robot.
        # Only future positions become movement waypoints.
        robot.destination = goal
        robot.waypoints = path[1:]
        robot.state = RobotState.MOVING
        robot.stuck_duration = 0.0

        return path

    def execute_recovery(self, action: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Execute recovery action decision produced by ExceptionHandlingAgent.

        Args:
            action: Recovery action dict with action_type, robot_id, waypoints, notes.

        Returns:
            Updated action dict with execution results or None if invalid.
        """
        if not action:
            return None

        robot_id = action.get("robot_id")
        robot = self.robots.get(robot_id)
        if robot is None:
            logger.warning("Recovery execution failed: robot %s not found.", robot_id)
            return action

        action_type = action.get("action_type")

        if action_type == "REROUTE":
            # Use real existing task destination/goal if one is already available
            goal = action.get("goal") or action.get("destination") or robot.destination
            if not goal and robot.waypoints:
                goal = robot.waypoints[-1]

            if goal:
                path = self.reroute_robot(robot_id, goal)
                action["waypoints"] = path[1:] if len(path) > 1 else path
            else:
                logger.warning("Reroute requested for %s but no existing goal/destination available.", robot_id)
            return action

        elif action_type == "RETURN_TO_CHARGER":
            if not self.grid.charging_stations:
                logger.warning("No charging stations configured on grid for %s.", robot_id)
                return action

            # Select appropriate charging station from WarehouseGrid (closest by Manhattan distance)
            charger = min(
                sorted(self.grid.charging_stations),
                key=lambda c: abs(c[0] - robot.position[0]) + abs(c[1] - robot.position[1])
            )

            if robot.position == charger:
                robot.state = RobotState.CHARGING
                robot.destination = charger
                robot.waypoints = []
                robot.stuck_duration = 0.0
                action["waypoints"] = []
            else:
                path = self.reroute_robot(robot_id, charger)
                action["waypoints"] = path[1:] if len(path) > 1 else path

            return action

        elif action_type == "ESCALATE_TO_HUMAN":
            # Preserve existing action and log appropriately using standard logger
            logger.warning(
                "Recovery escalation to human for robot %s: %s",
                robot_id,
                action.get("notes", "No details")
            )
            return action

        return action

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
            # If robot reached a charging dock and is idle, begin charging
            if (
                robot.state == RobotState.IDLE
                and robot.destination in self.grid.charging_stations
                and robot.position == robot.destination
                and robot.battery < 99.0
            ):
                robot.state = RobotState.CHARGING
            anomaly = self.sensor_generator.maybe_inject_anomaly(robot)
            if anomaly:
                anomalies.append(anomaly)
        return anomalies
