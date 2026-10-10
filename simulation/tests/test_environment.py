"""
Tests for WarehouseEnvironment rerouting.
"""

from simulation.environment import WarehouseEnvironment
from simulation.robot import RobotState


def test_environment_reroutes_stuck_robot():
    env = WarehouseEnvironment(width=10, height=10, num_robots=1)

    robot = env.robots["R1"]

    # Put the robot at a known position.
    robot.position = (1, 1)
    robot.state = RobotState.STUCK

    # Block the direct route to force A* to find a detour.
    env.grid.blocked_cells.add((2, 1))

    path = env.reroute_robot(
        robot_id="R1",
        goal=(5, 1)
    )

    assert path
    assert path[0] == (1, 1)
    assert path[-1] == (5, 1)
    assert not any(position == (2, 1) for position in path)

    # Robot should now be ready to follow the new route.
    assert robot.state == RobotState.MOVING
    assert robot.waypoints == path[1:]
    assert robot.stuck_duration == 0.0


def test_dispatch_order_two_stage_route_shelf_to_station():
    """
    Verifies that for 'Fetch 2 medical kits from Shelf-A1 to Station-1',
    the route travels: Current Pos -> Shelf-A1 -> Station-1.
    """
    env = WarehouseEnvironment(width=20, height=15, num_robots=1)
    robot = env.robots["R1"]
    robot.position = (1, 13)  # Charging bay

    path = env.dispatch_order_to_robot(
        robot_id="R1",
        source_name="Shelf-A1",
        destination_name="Station-1",
        task_description="Fetch 2 medical kits from Shelf-A1 to Station-1"
    )

    assert path, "Path should not be empty"
    assert path[0] == (1, 13)
    assert path[-1] == (15, 12)
    # Shelf-A1 is at (3, 3)
    assert (3, 3) in path, "Shelf-A1 (3, 3) must be visited along the route"
    
    # Verify sequence: Shelf-A1 comes before Station-1
    shelf_index = path.index((3, 3))
    station_index = path.index((15, 12))
    assert shelf_index < station_index, "Shelf-A1 must be reached before Station-1"

    # Verify robot state
    assert robot.state == RobotState.MOVING
    assert robot.intermediate_target == (3, 3)
    assert robot.destination == (15, 12)
    assert robot.final_destination == (15, 12)

    # Step simulation until Shelf-A1 is reached
    steps = 0
    while robot.position != (3, 3) and steps < 30:
        env.tick(delta_time=0.5)
        steps += 1

    assert robot.position == (3, 3)
    # Upon reaching Shelf-A1, intermediate_target should be cleared
    assert robot.intermediate_target is None
    # Robot continues moving to final destination Station-1
    assert robot.destination == (15, 12)


def test_inject_anomaly_and_detection():
    """Verify inject_anomaly sets physical robot states and simulation tick detects them."""
    env = WarehouseEnvironment(width=20, height=15, num_robots=1)
    robot = env.robots["R1"]

    # 1. Stuck anomaly
    res_stuck = env.inject_anomaly("R1", "stuck")
    assert res_stuck["anomaly_type"] == "ROBOT_STUCK"
    assert robot.state == RobotState.STUCK
    assert robot.stuck_duration >= 10.0

    anomalies = env.tick(delta_time=0.5)
    assert any(a["event_type"] == "ROBOT_STUCK" and a["robot_id"] == "R1" for a in anomalies)

    # Reset
    robot.state = RobotState.IDLE
    robot.stuck_duration = 0.0

    # 2. Low battery anomaly
    res_battery = env.inject_anomaly("R1", "low_battery")
    assert res_battery["anomaly_type"] == "LOW_BATTERY"
    assert robot.battery <= 15.0

    anomalies = env.tick(delta_time=0.5)
    assert any(a["event_type"] == "LOW_BATTERY" and a["robot_id"] == "R1" for a in anomalies)

    # 3. Dynamic obstacle and path blocking
    robot.battery = 100.0
    robot.position = (2, 2)
    robot.waypoints = [(2, 3), (2, 4)]
    robot.state = RobotState.MOVING

    res_block = env.inject_anomaly("R1", "block_path")
    assert res_block["anomaly_type"] == "PATH_BLOCKED"
    assert (2, 3) in env.grid.blocked_cells
    assert (2, 3) in env.dynamic_blocked_cells

    # Clear dynamic obstacles
    env.clear_dynamic_obstacles()
    assert (2, 3) not in env.grid.blocked_cells
    assert len(env.dynamic_blocked_cells) == 0


def test_reroute_preserves_two_stage_intermediate_target():
    """Verify reroute around an obstacle still visits the intermediate pickup location."""
    env = WarehouseEnvironment(width=20, height=15, num_robots=1)
    robot = env.robots["R1"]
    robot.position = (1, 13)

    # Dispatch route (1, 13) -> (3, 3) -> (15, 12)
    env.dispatch_order_to_robot(
        robot_id="R1",
        source_name="Shelf-A1",
        destination_name="Station-1"
    )

    # Block direct path between (1, 13) and (3, 3) at (1, 10)
    env.grid.blocked_cells.add((1, 10))

    # Trigger reroute
    rerouted_path = env.reroute_robot("R1", goal=robot.destination)
    assert rerouted_path
    assert not any(p == (1, 10) for p in rerouted_path)
    # The rerouted path must still visit Shelf-A1 (3, 3) and end at Station-1 (15, 12)
    assert (3, 3) in rerouted_path
    assert rerouted_path[-1] == (15, 12)
    assert rerouted_path.index((3, 3)) < rerouted_path.index((15, 12))