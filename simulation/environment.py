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
                if robot.state == RobotState.STUCK:
                    robot.state = RobotState.IDLE
                    robot.stuck_duration = 0.0
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

    def get_available_robots(self) -> List[Dict[str, Any]]:
        """Return array of enabled available robots for task assignment."""
        return [
            robot.to_telemetry() for robot in self.robots.values()
            if robot.enabled and robot.state != RobotState.ERROR
        ]

    def get_robot(self, robot_id: str) -> Optional[Robot]:
        """Get single Robot instance by ID."""
        return self.robots.get(robot_id)

    def add_robot(
        self,
        robot_id: str,
        name: Optional[str] = None,
        model: str = "AMR",
        capabilities: Optional[List[str]] = None,
        initial_position: Optional[List[int]] = None,
        battery: float = 100.0
    ) -> Robot:
        """
        Dynamically register a new AMR in the fleet and simulation runtime.
        """
        if not robot_id or not str(robot_id).strip():
            raise ValueError("Robot ID cannot be empty.")
        
        robot_id = str(robot_id).strip()
        if robot_id in self.robots:
            raise ValueError(f"Robot with ID '{robot_id}' already exists.")

        if battery < 0.0 or battery > 100.0:
            raise ValueError("Battery must be between 0.0 and 100.0.")

        pos = (0, 0)
        if initial_position:
            if len(initial_position) != 2:
                raise ValueError("Initial position must be an [x, y] coordinate array.")
            x, y = initial_position[0], initial_position[1]
            if x < 0 or x >= self.grid.width or y < 0 or y >= self.grid.height:
                raise ValueError(f"Position [{x}, {y}] is outside grid bounds ({self.grid.width}x{self.grid.height}).")
            pos = (x, y)
        else:
            charging_coords = list(self.grid.charging_stations)
            pos = charging_coords[len(self.robots) % len(charging_coords)]

        robot_name = name.strip() if name and name.strip() else f"Warehouse Robot {robot_id}"

        new_robot = Robot(
            robot_id=robot_id,
            start_pos=pos,
            battery=battery,
            name=robot_name,
            model=model or "AMR",
            capabilities=capabilities or ["transport", "pallet"],
            enabled=True
        )
        self.robots[robot_id] = new_robot
        return new_robot

    def update_robot(
        self,
        robot_id: str,
        name: Optional[str] = None,
        capabilities: Optional[List[str]] = None,
        enabled: Optional[bool] = None
    ) -> Robot:
        """Safely update non-simulation metadata fields of an existing robot."""
        robot = self.get_robot(robot_id)
        if not robot:
            raise ValueError(f"Robot '{robot_id}' not found.")

        if name is not None:
            if not name.strip():
                raise ValueError("Robot name cannot be empty.")
            robot.name = name.strip()

        if capabilities is not None:
            robot.capabilities = capabilities

        if enabled is not None:
            self.set_robot_enabled(robot_id, enabled)

        return robot

    def set_robot_enabled(self, robot_id: str, enabled: bool) -> Robot:
        """Enable or disable a robot safely."""
        robot = self.get_robot(robot_id)
        if not robot:
            raise ValueError(f"Robot '{robot_id}' not found.")

        if not enabled and robot.state in (RobotState.MOVING, RobotState.PICKING):
            raise ValueError(f"Cannot disable robot '{robot_id}' while executing task in state '{robot.state.value}'.")

        robot.enabled = enabled
        return robot

    def tick(self, delta_time: float = 0.5) -> List[Dict[str, Any]]:
        """
        Advance one simulation time step for all enabled robots.
        
        Returns:
            List of any anomaly events triggered during this tick.
        """
        anomalies = []
        for robot in self.robots.values():
            if robot.enabled:
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
