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