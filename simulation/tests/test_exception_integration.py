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