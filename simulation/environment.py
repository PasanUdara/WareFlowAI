"""
Warehouse Simulation Environment [Member 2]
Coordinates the 2D grid, AMR fleet lifecycle, and telemetry tick loop.
"""
import logging
import re
import time
from agents.exception_handling.logic.rerouter import Rerouter
from typing import Dict, List, Any, Optional, Set, Tuple
from .grid import WarehouseGrid
from .robot import Robot, RobotState
from .sensor_events import SensorEventGenerator

logger = logging.getLogger(__name__)

# Semantic warehouse location name to walkable grid coordinates mapping
LOCATION_MAP: Dict[str, Tuple[int, int]] = {
    # Shelf A (Access via Aisle 1 at cols 3 / 5)
    "shelf-a1": (3, 3),
    "shelf a1": (3, 3),
    "shelf-a2": (3, 4),
    "shelf a2": (3, 4),
    "shelf-a3": (3, 5),
    "shelf a3": (3, 5),
    "shelf-a": (3, 3),
    "shelf a": (3, 3),
    "shelf deck a": (3, 3),
    "shelf deck-a": (3, 3),
    "shelf deck b": (8, 3),
    "shelf deck-b": (8, 3),
    "shelf deck c": (11, 3),
    "shelf deck-c": (11, 3),
    "shelf deck d": (14, 3),
    "shelf deck-d": (14, 3),
    # Shelf B (Access via Aisle 2 at col 8)
    "shelf-b1": (8, 3),
    "shelf b1": (8, 3),
    "shelf-b2": (8, 4),
    "shelf b2": (8, 4),
    "shelf-b3": (8, 5),
    "shelf b3": (8, 5),
    "shelf-b": (8, 3),
    "shelf b": (8, 3),
    # Shelf C (Access via Aisle 3 at col 11)
    "shelf-c1": (11, 3),
    "shelf c1": (11, 3),
    "shelf-c2": (11, 4),
    "shelf c2": (11, 4),
    "shelf-c3": (11, 5),
    "shelf c3": (11, 5),
    "shelf-c": (11, 3),
    "shelf c": (11, 3),
    # Shelf D (Access via Aisle 4 at col 14)
    "shelf-d1": (14, 3),
    "shelf d1": (14, 3),
    "shelf-d2": (14, 4),
    "shelf d2": (14, 4),
    "shelf-d3": (14, 5),
    "shelf d3": (14, 5),
    "shelf-d": (14, 3),
    "shelf d": (14, 3),
    # Packing Stations (Workstations at bottom-right)
    "station-1": (15, 12),
    "station 1": (15, 12),
    "station-2": (16, 12),
    "station 2": (16, 12),
    "station-3": (17, 12),
    "station 3": (17, 12),
    "packing station": (16, 12),
    "packing station 1": (15, 12),
    "packing station-1": (15, 12),
    "packing station 2": (16, 12),
    "packing station-2": (16, 12),
    "packing station 3": (17, 12),
    "packing station-3": (17, 12),
    # Receiving Dock (Top-left)
    "receiving": (2, 1),
    "receiving dock": (2, 1),
    "receiving-dock": (2, 1),
    # Charging Bay (Bottom-left)
    "charging": (2, 13),
    "charging bay": (2, 13),
    "charging-bay": (2, 13),
    "charging station": (2, 13),
    "charger": (2, 13),
    # Hazmat Zone
    "hazmat aisle 4": (11, 5),
    "hazmat aisle-4": (11, 5),
    "hazmat": (11, 5),
}


class WarehouseEnvironment:
    """Discrete-time warehouse simulation runtime."""

    def __init__(self, width: int = 20, height: int = 15, num_robots: int = 4):
        self.grid = WarehouseGrid(width=width, height=height)
        self.robots: Dict[str, Robot] = {}
        self.sensor_generator = SensorEventGenerator()
        self.dynamic_blocked_cells: Set[Tuple[int, int]] = set()
        self.task_queue: List[Dict[str, Any]] = []
        self._init_fleet(num_robots)

    def queue_order(self, order_dict: Dict[str, Any]) -> int:
        """Enqueue pending order when all fleet robots are active. Returns 1-based queue position."""
        self.task_queue.append(order_dict)
        return len(self.task_queue)

    def get_task_queue(self) -> List[Dict[str, Any]]:
        """Return snapshot of currently queued orders."""
        return [dict(t) for t in self.task_queue]

        
    def _init_fleet(self, num_robots: int):
        """Spawns AMRs at initial charging stations."""
        charging_coords = sorted(list(self.grid.charging_stations))
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

        # If a full order sentence was passed, extract the source pickup clause first
        m_from = re.search(r"\bfrom\s+(.*?)(?:\s+to\s+|$)", clean_name)
        if m_from:
            extracted_src = m_from.group(1).strip()
            res = self.resolve_location(extracted_src)
            if res:
                return res

        if clean_name in LOCATION_MAP:
            return self._ensure_walkable(LOCATION_MAP[clean_name])

        # Heuristic keyword matching
        if "shelf" in clean_name and "a1" in clean_name:
            return self._ensure_walkable((3, 3))
        if "shelf" in clean_name and "a2" in clean_name:
            return self._ensure_walkable((3, 4))
        if "shelf" in clean_name and "a3" in clean_name:
            return self._ensure_walkable((3, 5))
        if "shelf" in clean_name and (" a" in clean_name or "-a" in clean_name or clean_name.endswith("a")):
            return self._ensure_walkable((3, 3))

        if "shelf" in clean_name and "b1" in clean_name:
            return self._ensure_walkable((8, 3))
        if "shelf" in clean_name and "b2" in clean_name:
            return self._ensure_walkable((8, 4))
        if "shelf" in clean_name and "b3" in clean_name:
            return self._ensure_walkable((8, 5))
        if "shelf" in clean_name and (" b" in clean_name or "-b" in clean_name or clean_name.endswith("b")):
            return self._ensure_walkable((8, 3))

        if "shelf" in clean_name and "c1" in clean_name:
            return self._ensure_walkable((11, 3))
        if "shelf" in clean_name and "c2" in clean_name:
            return self._ensure_walkable((11, 4))
        if "shelf" in clean_name and "c3" in clean_name:
            return self._ensure_walkable((11, 5))
        if "shelf" in clean_name and (" c" in clean_name or "-c" in clean_name or clean_name.endswith("c")):
            return self._ensure_walkable((11, 3))

        if "shelf" in clean_name and "d1" in clean_name:
            return self._ensure_walkable((14, 3))
        if "shelf" in clean_name and "d2" in clean_name:
            return self._ensure_walkable((14, 4))
        if "shelf" in clean_name and "d3" in clean_name:
            return self._ensure_walkable((14, 5))
        if "shelf" in clean_name and (" d" in clean_name or "-d" in clean_name or clean_name.endswith("d")):
            return self._ensure_walkable((14, 3))
        if "station" in clean_name and "1" in clean_name:
            return self._ensure_walkable((15, 12))
        if "station" in clean_name and "2" in clean_name:
            return self._ensure_walkable((16, 12))
        if "station" in clean_name and "3" in clean_name:
            return self._ensure_walkable((17, 12))
        if "packing" in clean_name:
            return self._ensure_walkable((16, 12))
        if "charging" in clean_name or "charger" in clean_name:
            return self._ensure_walkable((2, 13))
        if "receiving" in clean_name:
            return self._ensure_walkable((2, 1))
        if "hazmat" in clean_name:
            return self._ensure_walkable((11, 5))

        # Default fallback to drop-off packing station
        return self._ensure_walkable((16, 12))

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
        task_description: Optional[str] = None,
        item: Optional[str] = None,
        qty: Optional[int] = None,
        sub_orders: Optional[List[Dict[str, Any]]] = None
    ) -> List[Tuple[int, int]]:
        """
        Dispatches an order to an AMR by mapping source and destination to grid coordinates.
        Supports single orders as well as multi-drop compound orders originating from a shared source:
        1. If sub_orders are provided (or extracted from task_description) sharing a source:
           - Batches all items together at the source.
           - Calculates distance from the shared source to all candidate destinations.
           - Sorts destinations by distance from source in ascending order (nearest first).
           - Computes collision-free A* detour route: Robot -> Source -> Stop 1 -> Stop 2 -> ... -> Stop N.
           - Robot loads all items at source (with loading duration), unloads at Stop 1 (with unloading duration),
             resumes travel to Stop 2, unloads at Stop 2, and completes to IDLE.
        """
        robot = self.robots.get(robot_id)
        if not robot:
            logger.warning("Cannot dispatch order: robot %s not found.", robot_id)
            return []

        # If sub_orders not passed explicitly, attempt extraction from task_description as a fallback
        if not sub_orders and task_description:
            try:
                from agents.task_planning.nodes.parse_order import _rule_based_parse_order
                parsed_check = _rule_based_parse_order(task_description)
                if parsed_check and parsed_check.get("multi_drop"):
                    sub_orders = parsed_check.get("sub_orders")
            except Exception as e:
                logger.debug("Fallback rule_based_parse_order in dispatch_order_to_robot: %s", e)

        rerouter = Rerouter()
        grid_bounds = (self.grid.width, self.grid.height)

        # Check if this is a multi-drop order sharing a source
        is_multi_drop = False
        ordered_stops: List[Dict[str, Any]] = []
        combined_item_str = item or "pallets"
        source_pos = self.resolve_location(source_name)

        if sub_orders and len(sub_orders) >= 2:
            resolved_srcs = [self.resolve_location(so.get("source")) for so in sub_orders if so.get("source")]
            if resolved_srcs and all(s == resolved_srcs[0] for s in resolved_srcs):
                is_multi_drop = True
                source_pos = resolved_srcs[0]
                source_name = sub_orders[0].get("source") or source_name

                # Combine item summary (e.g. "5 pallets & 3 tiles pack")
                item_labels = [f"{so.get('quantity', 1)} {so.get('item', 'items')}".strip() for so in sub_orders]
                combined_item_str = " & ".join(item_labels)

                # Prepare candidate delivery stops with distance from source_pos
                candidate_stops = []
                for idx, so in enumerate(sub_orders):
                    dst_name = so.get("destination") or "destination"
                    dst_pos = self.resolve_location(dst_name) or (16, 12)
                    dist = abs(dst_pos[0] - source_pos[0]) + abs(dst_pos[1] - source_pos[1])
                    candidate_stops.append({
                        "name": dst_name,
                        "location": dst_pos,
                        "item": f"{so.get('quantity', 1)} {so.get('item', 'items')}".strip(),
                        "quantity": so.get("quantity", 1),
                        "dist_from_source": dist,
                        "original_index": idx
                    })

                # Sort by distance from source: NEAREST FIRST!
                ordered_stops = sorted(candidate_stops, key=lambda s: (s["dist_from_source"], s["original_index"]))

        if not is_multi_drop:
            # Single-destination order
            dest_pos = self.resolve_location(destination_name) or (16, 12)
            ref_pos = source_pos or robot.position
            dist = abs(dest_pos[0] - ref_pos[0]) + abs(dest_pos[1] - ref_pos[1])
            ordered_stops = [{
                "name": destination_name or "destination",
                "location": dest_pos,
                "item": item or "pallets",
                "quantity": qty or 1,
                "dist_from_source": dist
            }]
        else:
            dest_pos = ordered_stops[-1]["location"]

        # Compute multi-leg collision-free path:
        # Leg 0: robot.position -> source_pos (if source specified and robot not already there)
        # Leg 1: source_pos -> stop 1
        # Leg 2: stop 1 -> stop 2 ...
        full_path: List[Tuple[int, int]] = []
        if source_pos and source_pos != robot.position:
            path_to_source = rerouter.calculate_detour(
                start=robot.position,
                goal=source_pos,
                blocked_cells=self.grid.blocked_cells,
                grid_bounds=grid_bounds
            )
            if path_to_source:
                full_path.extend(path_to_source)
            current_from = source_pos
        else:
            current_from = robot.position

        for stop in ordered_stops:
            leg = rerouter.calculate_detour(
                start=current_from,
                goal=stop["location"],
                blocked_cells=self.grid.blocked_cells,
                grid_bounds=grid_bounds
            )
            if leg:
                if full_path:
                    full_path.extend(leg[1:] if len(leg) > 1 else [])
                else:
                    full_path.extend(leg)
                current_from = stop["location"]

        waypoints = full_path[1:] if len(full_path) > 1 else []
        if not waypoints:
            logger.warning("No waypoints generated for robot %s to %s (already at destination or empty path).", robot_id, dest_pos)
            robot.destination = dest_pos
            robot.final_destination = dest_pos
            robot.intermediate_target = None
            robot.waypoints = []
            robot.delivery_stops = []
            robot.current_stop_index = 0
            robot.state = RobotState.IDLE
            return full_path

        first_stop = ordered_stops[0]
        final_stop = ordered_stops[-1]

        robot.destination = first_stop["location"]
        robot.destination_name = first_stop["name"]
        robot.final_destination = final_stop["location"]
        robot.intermediate_target = source_pos if (source_pos and source_pos != robot.position) else None
        robot.waypoints = waypoints
        robot.delivery_stops = [
            {
                "name": s["name"],
                "location": s["location"],
                "item": s["item"],
                "quantity": s.get("quantity", 1)
            }
            for s in ordered_stops
        ]
        robot.current_stop_index = 0
        robot.state = RobotState.MOVING
        robot.is_rerouted = False
        robot.stuck_duration = 0.0
        robot.current_task_id = task_description or f"Order: {source_name} to {final_stop['name']}"

        # Initialize source, item and loading tracker
        robot.source_pos = source_pos
        robot.source_name = source_name
        robot.item = combined_item_str
        robot.source_active = bool(source_pos and source_pos != robot.position)
        robot.loading_duration = 0.0
        robot.unloading_duration = 0.0

        if not robot.source_active:
            if source_pos == robot.position:
                robot.state = RobotState.PICKING
                robot.loading_duration = 3.0
                robot.loaded = False
                robot.status_text = f"Loading all items ({robot.item}) from {robot.source_name or 'source'} (3s)..."
            else:
                robot.loaded = True
                robot.status_text = f"Heading to {first_stop['name']}"
        else:
            robot.loaded = False
            robot.status_text = f"Heading to {source_name or 'source'} to collect {robot.item}"

        logger.info(
            "Dispatched robot %s along %d waypoints (Stops: %s, Goal: %s via %s)",
            robot_id, len(robot.waypoints), [s['name'] for s in ordered_stops], final_stop['location'], source_pos
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
                goal = (16, 12)

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

            # If robot had an in-flight mission when battery dropped, re-queue task so another AMR completes it
            if getattr(robot, "source_name", None) and getattr(robot, "destination_name", None) and not getattr(robot, "requeued_on_low_battery", False):
                robot.requeued_on_low_battery = True
                self.task_queue.insert(0, {
                    "order_id": f"RETRY-{robot.robot_id}",
                    "order_text": f"Move {robot.item or 'items'} from {robot.source_name} to {robot.destination_name}",
                    "source_name": robot.source_name,
                    "destination_name": robot.destination_name,
                    "item": robot.item or "pallets",
                    "qty": 1,
                    "timestamp": time.time()
                })

            if robot.position == charger:
                robot.state = RobotState.CHARGING
                robot.destination = charger
                robot.waypoints = []
                robot.stuck_duration = 0.0
                robot.status_text = f"Recharging battery ({int(round(robot.battery))}%)..."
                action["waypoints"] = []
            else:
                path = self.reroute_robot(robot_id, charger)
                robot.source_active = False
                robot.loaded = False
                robot.status_text = f"Low Battery ({robot.battery:.0f}%) → Navigating to Charging Bay"
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
                    robot.status_text = f"Recharging battery ({int(round(robot.battery))}%)..."
                # Check physical anomaly conditions on active robot (low battery <= 20.0)
                if (
                    robot.battery <= 20.0
                    and robot.state != RobotState.CHARGING
                    and (not robot.destination or robot.destination not in self.grid.charging_stations)
                ):
                    anomalies.append({
                        "event_type": "LOW_BATTERY",
                        "robot_id": robot.robot_id,
                        "battery": round(robot.battery, 1),
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

        # Process pending task queue if any idle robots are available
        if self.task_queue:
            idle_robots = [
                r for r in self.robots.values()
                if r.enabled and r.state == RobotState.IDLE and not r.waypoints and r.battery > 20.0
            ]
            if idle_robots:
                next_order = self.task_queue.pop(0)
                parsed_dict = next_order.get("parsed_order") or {}
                source_name = next_order.get("source_name") or parsed_dict.get("source")
                destination_name = next_order.get("destination_name") or parsed_dict.get("destination")
                sub_orders = next_order.get("sub_orders") or parsed_dict.get("sub_orders")
                item = next_order.get("item") or parsed_dict.get("item")
                qty = next_order.get("qty") or parsed_dict.get("quantity")
                source_pos = self.resolve_location(source_name)

                # Prioritize nearest idle robot to the source position (closest first, higher battery tie-breaker)
                if source_pos:
                    best_robot = min(
                        idle_robots,
                        key=lambda r: (
                            abs(r.position[0] - source_pos[0]) + abs(r.position[1] - source_pos[1]),
                            -float(r.battery)
                        )
                    )
                else:
                    best_robot = max(idle_robots, key=lambda r: float(r.battery))

                logger.info(
                    "Auto-dispatching queued order '%s' to nearest idle robot %s at %s",
                    next_order.get("order_text"),
                    best_robot.robot_id,
                    best_robot.position
                )
                self.dispatch_order_to_robot(
                    robot_id=best_robot.robot_id,
                    source_name=source_name,
                    destination_name=destination_name,
                    task_description=next_order.get("order_text"),
                    item=item,
                    qty=qty,
                    sub_orders=sub_orders
                )

        return anomalies
