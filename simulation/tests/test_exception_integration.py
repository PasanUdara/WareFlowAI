"""
Integration test for the Member 2 exception-handling flow.
"""

from agents.exception_handling.agent import ExceptionHandlingAgent
from simulation.environment import WarehouseEnvironment
from simulation.robot import RobotState


def test_stuck_robot_exception_to_reroute_flow():
    env = WarehouseEnvironment(
        width=10,
        height=10,
        num_robots=1
    )

    robot = env.robots["R1"]

    # Put the robot at a known position.
    robot.position = (1, 1)
    robot.state = RobotState.STUCK
    robot.stuck_duration = 12.0

    # Block the direct route.
    env.grid.blocked_cells.add((2, 1))

    # Create the exception-handling agent.
    exception_agent = ExceptionHandlingAgent()

    # Send the robot telemetry to the exception agent.
    telemetry = robot.to_telemetry()

    action = exception_agent.process_telemetry_event(telemetry)

    # Exception agent should request a reroute.
    assert action is not None
    assert action["action_type"] == "REROUTE"
    assert action["robot_id"] == "R1"

    # Apply the recovery decision through the simulation environment.
    path = env.reroute_robot(
        robot_id="R1",
        goal=(5, 1)
    )

    # A* should produce a valid alternate route.
    assert path
    assert path[0] == (1, 1)
    assert path[-1] == (5, 1)
    assert not any(position == (2, 1) for position in path)

    # Robot should now be moving again.
    assert robot.state == RobotState.MOVING
    assert robot.waypoints == path[1:]


def test_stuck_robot_automated_recovery_execution():
    """Verify end-to-end flow: detection -> REROUTE -> simulation execution -> path & state change."""
    env = WarehouseEnvironment(width=10, height=10, num_robots=1)
    robot = env.robots["R1"]

    # Robot has an active goal and is at (1, 1)
    robot.position = (1, 1)
    robot.destination = (5, 1)
    robot.state = RobotState.STUCK
    robot.stuck_duration = 12.0

    # Obstacle blocks direct line
    env.grid.blocked_cells.add((2, 1))

    exception_agent = ExceptionHandlingAgent()
    telemetry = robot.to_telemetry()

    # Step 1: Detect anomaly and produce recovery decision
    action = exception_agent.process_telemetry_event(telemetry)
    assert action is not None
    assert action["action_type"] == "REROUTE"
    assert action["robot_id"] == "R1"

    # Step 2: Simulation executes recovery using the real robot destination
    executed_action = env.execute_recovery(action)
    assert executed_action is not None
    assert len(executed_action["waypoints"]) > 0

    # Step 3: Verify state and waypoints
    assert robot.state == RobotState.MOVING
    assert robot.stuck_duration == 0.0
    assert robot.waypoints == executed_action["waypoints"]
    assert not any(pos == (2, 1) for pos in robot.waypoints)
    assert robot.waypoints[-1] == (5, 1)

    # Step 4: Advance tick and verify movement
    first_wp = robot.waypoints[0]
    env.tick(delta_time=0.5)
    assert robot.position == first_wp


def test_low_battery_automated_recovery_to_grid_charger():
    """Verify critical battery triggers RETURN_TO_CHARGER and simulation routes to existing WarehouseGrid charger."""
    env = WarehouseEnvironment(width=10, height=10, num_robots=1)
    robot = env.robots["R1"]

    # Place robot far from charger docks (which are along top wall y=0)
    robot.position = (3, 5)
    robot.battery = 10.0
    robot.state = RobotState.MOVING

    exception_agent = ExceptionHandlingAgent()
    telemetry = robot.to_telemetry()

    # Step 1: Detection
    action = exception_agent.process_telemetry_event(telemetry)
    assert action is not None
    assert action["action_type"] == "RETURN_TO_CHARGER"

    # Step 2: Recovery execution routes to an existing charger
    executed_action = env.execute_recovery(action)
    assert executed_action is not None
    assert robot.destination in env.grid.charging_stations
    assert robot.state == RobotState.MOVING
    assert len(robot.waypoints) > 0
    assert robot.waypoints[-1] in env.grid.charging_stations

    # Step 3: If robot is already at charging dock, it transitions directly to CHARGING
    robot.position = robot.destination
    robot.waypoints = []
    env.execute_recovery(action)
    assert robot.state == RobotState.CHARGING

    # Step 4: Charging advances battery on simulation tick
    old_battery = robot.battery
    env.tick(delta_time=1.0)
    assert robot.battery > old_battery


def test_escalate_to_human_recovery_preservation():
    """Verify unhandled anomalies escalate to human without inventing new notification systems."""
    env = WarehouseEnvironment(width=10, height=10, num_robots=1)
    robot = env.robots["R1"]

    exception_agent = ExceptionHandlingAgent()
    event = {
        "event_type": "MOTOR_STALL",
        "robot_id": "R1",
        "position": (2, 2),
        "severity": "CRITICAL"
    }

    action = exception_agent.process_telemetry_event(event)
    assert action is not None
    assert action["action_type"] == "ESCALATE_TO_HUMAN"

    executed_action = env.execute_recovery(action)
    assert executed_action["action_type"] == "ESCALATE_TO_HUMAN"
    assert executed_action["robot_id"] == "R1"