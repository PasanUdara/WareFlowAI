"""
Test suite for Member 2 A* Rerouter.
"""

from agents.exception_handling.logic.rerouter import Rerouter


def test_rerouter_finds_simple_path():
    rerouter = Rerouter()

    path = rerouter.calculate_detour(
        start=(1, 1),
        goal=(5, 1),
        blocked_cells=set(),
        grid_bounds=(10, 10)
    )

    assert path
    assert path[0] == (1, 1)
    assert path[-1] == (5, 1)


def test_rerouter_avoids_blocked_cells():
    rerouter = Rerouter()

    blocked = {(2, 1)}

    path = rerouter.calculate_detour(
        start=(1, 1),
        goal=(5, 1),
        blocked_cells=blocked,
        grid_bounds=(10, 10)
    )

    assert path
    assert path[0] == (1, 1)
    assert path[-1] == (5, 1)
    assert not any(position in blocked for position in path)


def test_rerouter_returns_empty_when_no_path():
    rerouter = Rerouter()

    blocked = {
        (0, 1),
        (1, 0),
        (1, 2),
        (2, 1)
    }

    path = rerouter.calculate_detour(
        start=(1, 1),
        goal=(5, 5),
        blocked_cells=blocked,
        grid_bounds=(10, 10)
    )

    assert path == []
def test_rerouter_returns_waypoints_for_recovery():
    rerouter = Rerouter()

    path = rerouter.calculate_detour(
        start=(1, 1),
        goal=(5, 1),
        blocked_cells={(2, 1)},
        grid_bounds=(10, 10)
    )

    assert isinstance(path, list)
    assert len(path) > 0
    assert path[0] == (1, 1)
    assert path[-1] == (5, 1)
    assert not any(position == (2, 1) for position in path)