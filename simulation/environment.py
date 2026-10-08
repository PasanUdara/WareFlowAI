"""
Warehouse Simulation Environment [Member 2]
Coordinates the 2D grid, AMR fleet lifecycle, and telemetry tick loop.
"""
import logging
from agents.exception_handling.logic.rerouter import Rerouter
from typing import Dict, List, Any, Optional, Set, Tuple
from .grid import WarehouseGrid
from .robot import Robot, RobotState
from .sensor_events import SensorEventGenerator

logger = logging.getLogger(__name__)

# Semantic warehouse location name to walkable grid coordinates mapping
LOCATION_MAP: Dict[str, Tuple[int, int]] = {
    "shelf-a1": (3, 3),
    "shelf a1": (3, 3),
    "shelf-a2": (3, 4),
    "shelf a2": (3, 4),
    "shelf-b1": (6, 3),
    "shelf b1": (6, 3),
    "shelf-b2": (6, 4),
    "shelf b2": (6, 4),
    "station-1": (1, 14),
    "station 1": (1, 14),
    "station-2": (2, 14),
    "station 2": (2, 14),
    "packing station 1": (1, 14),
    "packing station 2": (2, 14),
    "packing station 3": (3, 14),
    "packing station-3": (3, 14),
    "receiving": (1, 1),
    "receiving dock": (1, 1),
    "hazmat aisle 4": (11, 5),
    "hazmat aisle-4": (11, 5),
}


class WarehouseEnvironment:
    """Discrete-time warehouse simulation runtime."""

    def __init__(self, width: int = 20, height: int = 15, num_robots: int = 4):
        self.grid = WarehouseGrid(width=width, height=height)
        self.robots: Dict[str, Robot] = {}
        self.sensor_generator = SensorEventGenerator()
        self.dynamic_blocked_cells: Set[Tuple[int, int]] = set()
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

    def resolve_location(self, name: Optional[str]) -> Optional[Tuple[int, int]]:
        """
        Resolve a warehouse location string (e.g. 'Shelf-A1', 'Station-1')
        to physical grid coordinates, ensuring the target is walkable.
        """
        if not name or not isinstance(name, str):
            return None

        clean_name = name.strip().lower().rstrip(".").rstrip(",")

        if clean_name in LOCATION_MAP:
            return self._ensure_walkable(LOCATION_MAP[clean_name])

        # Heuristic keyword matching
        if "shelf" in clean_name and "a1" in clean_name:
            return self._ensure_walkable((3, 3))
        if "shelf" in clean_name and "a2" in clean_name:
            return self._ensure_walkable((3, 4))
        if "shelf" in clean_name and "b1" in clean_name:
            return self._ensure_walkable((6, 3))
        if "shelf" in clean_name and "b2" in clean_name:
            return self._ensure_walkable((6, 4))
        if "station" in clean_name and "1" in clean_name:
            return self._ensure_walkable((1, 14))
        if "station" in clean_name and "2" in clean_name:
            return self._ensure_walkable((2, 14))
        if "station" in clean_name and "3" in clean_name:
            return self._ensure_walkable((3, 14))
        if "receiving" in clean_name:
            return self._ensure_walkable((1, 1))
        if "hazmat" in clean_name:
            return self._ensure_walkable((11, 5))

        # Default fallback to drop-off station
        return self._ensure_walkable((1, 14))

    def _ensure_walkable(self, coord: Tuple[int, int]) -> Tuple[int, int]:
        """Ensure coordinate is within bounds and not in blocked_cells."""
        x, y = coord
        if self.grid.is_walkable(x, y):
            return coord
        for dx, dy in [(0, -1), (0, 1), (-1, 0), (1, 0), (-1, -1), (1, 1)]:
            nx, ny = x + dx, y + dy
            if self.grid.is_walkable(nx, ny):
                return (nx, ny)
        return (1, 1)

    def dispatch_order_to_robot(
        self,
        robot_id: str,
        source_name: Optional[str] = None,
        destination_name: Optional[str] = None,
        task_description: Optional[str] = None
    ) -> List[Tuple[int, int]]:
        """
        Dispatches an order to an AMR by mapping source and destination to grid coordinates
        and calculating the logical route: Current Pos -> Source -> Destination.
        """
        robot = self.robots.get(robot_id)
        if not robot:
            logger.warning("Cannot dispatch order: robot %s not found.", robot_id)
            return []

        source_pos = self.resolve_location(source_name)
        dest_pos = self.resolve_location(destination_name) or (1, 14)

        rerouter = Rerouter()
        grid_bounds = (self.grid.width, self.grid.height)
        
        full_path: List[Tuple[int, int]] = []
        if source_pos and source_pos != robot.position:
            # Segment 1: robot.position -> source_pos
            path_to_source = rerouter.calculate_detour(
                start=robot.position,
                goal=source_pos,
                blocked_cells=self.grid.blocked_cells,
                grid_bounds=grid_bounds
            )
            # Segment 2: source_pos -> dest_pos
            path_to_dest = rerouter.calculate_detour(
                start=source_pos,
                goal=dest_pos,
                blocked_cells=self.grid.blocked_cells,
                grid_bounds=grid_bounds
            )

            if path_to_source:
                full_path.extend(path_to_source)
                if path_to_dest and len(path_to_dest) > 1:
                    full_path.extend(path_to_dest[1:])
            elif path_to_dest:
                full_path.extend(path_to_dest)
        else:
            full_path = rerouter.calculate_detour(
                start=robot.position,
                goal=dest_pos,
                blocked_cells=self.grid.blocked_cells,
                grid_bounds=grid_bounds
            )

        waypoints = full_path[1:] if len(full_path) > 1 else []
        if not waypoints:
            logger.warning("No waypoints generated for robot %s to %s (already at destination or empty path).", robot_id, dest_pos)
            robot.destination = dest_pos
            robot.final_destination = dest_pos
            robot.intermediate_target = None
            robot.waypoints = []
            robot.state = RobotState.IDLE
            return full_path

        robot.destination = dest_pos
        robot.intermediate_target = source_pos if (source_pos and source_pos != robot.position) else None
        robot.final_destination = dest_pos
        robot.waypoints = waypoints
        robot.state = RobotState.MOVING
        robot.is_rerouted = False
        robot.stuck_duration = 0.0
        robot.current_task_id = task_description or f"Order: {source_name} to {destination_name}"

        logger.info(
            "Dispatched robot %s along %d waypoints (Goal: %s via %s)",
            robot_id, len(robot.waypoints), dest_pos, source_pos
        )
        return full_path

    def reroute_robot(
        self,
        robot_id: str,
        goal: Tuple[int, int],
        intermediate: Optional[Tuple[int, int]] = None
    ) -> List[Tuple[int, int]]:
        """
        Calculate and apply an alternate A* route for a robot.

        Args:
            robot_id: ID of the robot that needs rerouting.
            goal: Intended destination on the warehouse grid.
            intermediate: Optional intermediate target (e.g. pickup shelf) to visit before destination.

        Returns:
            Calculated waypoint path. Returns an empty list if
            the robot does not exist or no valid path is available.
        """
        robot = self.robots.get(robot_id)

        if robot is None:
            return []

        rerouter = Rerouter()
        grid_bounds = (self.grid.width, self.grid.height)
        target_intermediate = intermediate if intermediate is not None else getattr(robot, "intermediate_target", None)

        full_path: List[Tuple[int, int]] = []
        if target_intermediate and target_intermediate != robot.position and target_intermediate != goal:
            path1 = rerouter.calculate_detour(
                start=robot.position,
                goal=target_intermediate,
                blocked_cells=self.grid.blocked_cells,
                grid_bounds=grid_bounds
            )
            path2 = rerouter.calculate_detour(
                start=target_intermediate,
                goal=goal,
                blocked_cells=self.grid.blocked_cells,
                grid_bounds=grid_bounds
            )
            if path1:
                full_path.extend(path1)
                if path2 and len(path2) > 1:
                    full_path.extend(path2[1:])
            elif path2:
                full_path.extend(path2)
        else:
            full_path = rerouter.calculate_detour(
                start=robot.position,
                goal=goal,
                blocked_cells=self.grid.blocked_cells,
                grid_bounds=grid_bounds
            )

        if not full_path:
            return []

        # Current position is already occupied by the robot.
        # Only future positions become movement waypoints.
        robot.destination = goal
        robot.final_destination = goal
        robot.intermediate_target = target_intermediate if (target_intermediate and target_intermediate != robot.position) else None
        robot.waypoints = full_path[1:]
        robot.state = RobotState.MOVING
        robot.is_rerouted = True
        robot.stuck_duration = 0.0

        return full_path

    def inject_anomaly(self, robot_id: str, anomaly_type: str) -> Dict[str, Any]:
        """
        Manually inject a synthetic anomaly condition on an AMR for testing and demonstration.
        Does NOT bypass the Exception Handling Agent: sets the physical condition on the robot,
        which will be detected on the next simulation tick.
        """
        robot = self.robots.get(robot_id)
        if not robot:
            raise ValueError(f"Robot '{robot_id}' not found.")

        clean_type = str(anomaly_type).strip().lower()

        if clean_type in ("stuck", "robot_stuck"):
            robot.state = RobotState.STUCK
            robot.stuck_duration = 12.0  # Above STALL_TIMEOUT_SECONDS = 10.0
            return {
                "robot_id": robot_id,
                "anomaly_type": "ROBOT_STUCK",
                "state": robot.state.value if hasattr(robot.state, "value") else str(robot.state),
                "stuck_duration": robot.stuck_duration,
                "position": robot.position,
                "severity": "HIGH",
                "message": f"Robot {robot_id} forced into STUCK state (duration: 12.0s)."
            }

        elif clean_type in ("low_battery", "battery"):
            robot.battery = 10.0  # Below BATTERY_CRITICAL_THRESHOLD = 15.0
            return {
                "robot_id": robot_id,
                "anomaly_type": "LOW_BATTERY",
                "battery": robot.battery,
                "position": robot.position,
                "severity": "CRITICAL",
                "message": f"Robot {robot_id} battery drained to 10.0% (Critical)."
            }

        elif clean_type in ("block_path", "path_blocked"):
            # Block the robot's upcoming waypoint
            blocked_coord = None
            if robot.waypoints:
                blocked_coord = robot.waypoints[0]
            else:
                blocked_coord = (min(self.grid.width - 1, robot.position[0] + 1), robot.position[1])

            self.grid.blocked_cells.add(blocked_coord)
            self.dynamic_blocked_cells.add(blocked_coord)
            robot.state = RobotState.STUCK
            robot.stuck_duration = 12.0
            return {
                "robot_id": robot_id,
                "anomaly_type": "PATH_BLOCKED",
                "blocked_cell": list(blocked_coord),
                "position": robot.position,
                "severity": "HIGH",
                "message": f"Obstacle placed at {blocked_coord}. Robot {robot_id} path blocked."
            }

        else:
            raise ValueError(f"Unsupported anomaly type '{anomaly_type}'. Supported: 'stuck', 'low_battery', 'block_path'.")

    def clear_dynamic_obstacles(self):
        """Remove dynamically injected obstacles and restore grid to default layout."""
        for cell in list(self.dynamic_blocked_cells):
            self.grid.blocked_cells.discard(cell)
        self.dynamic_blocked_cells.clear()

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
            goal = (
                action.get("goal")
                or action.get("destination")
                or robot.destination
                or getattr(robot, "final_destination", None)
            )
            if not goal and robot.waypoints:
                goal = robot.waypoints[-1]
            if not goal:
                goal = (1, 14)

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

                # Check physical anomaly conditions on the active robot
                if (
                    robot.battery < 15.0
                    and robot.state != RobotState.CHARGING
                    and (not robot.destination or robot.destination not in self.grid.charging_stations)
                ):
                    anomalies.append({
                        "event_type": "LOW_BATTERY",
                        "robot_id": robot.robot_id,
                        "battery": robot.battery,
                        "position": robot.position,
                        "severity": "CRITICAL"
                    })
                elif robot.state == RobotState.STUCK or robot.stuck_duration > 10.0:
                    anomalies.append({
                        "event_type": "ROBOT_STUCK",
                        "robot_id": robot.robot_id,
                        "position": robot.position,
                        "state": robot.state.value if hasattr(robot.state, "value") else str(robot.state),
                        "stuck_duration": robot.stuck_duration,
                        "battery": robot.battery,
                        "severity": "HIGH"
                    })
                else:
                    anomaly = self.sensor_generator.maybe_inject_anomaly(robot)
                    if anomaly:
                        anomalies.append(anomaly)
        return anomalies
