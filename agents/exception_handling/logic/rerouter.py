"""
Pathfinder & Rerouter [Member 2]
Calculates alternate waypoints for AMRs when primary routes are blocked.
"""

import heapq
from typing import List, Tuple, Set


class Rerouter:
    """Provides path recalculation avoiding blocked grid cells."""

    def calculate_detour(
        self,
        start: Tuple[int, int],
        goal: Tuple[int, int],
        blocked_cells: Set[Tuple[int, int]],
        grid_bounds: Tuple[int, int] = (20, 15)
    ) -> List[Tuple[int, int]]:
        """
        Calculate the shortest valid path from start to goal
        using A* while avoiding blocked cells.
        """

        width, height = grid_bounds

        def is_valid(position: Tuple[int, int]) -> bool:
            x, y = position
            return (
                0 <= x < width
                and 0 <= y < height
                and position not in blocked_cells
            )

        def heuristic(
            position: Tuple[int, int],
            target: Tuple[int, int]
        ) -> int:
            """Manhattan distance heuristic."""
            return abs(position[0] - target[0]) + abs(position[1] - target[1])

        if not is_valid(start) or not is_valid(goal):
            return []

        open_set = []
        heapq.heappush(open_set, (heuristic(start, goal), 0, start))

        came_from = {}
        g_score = {start: 0}

        directions = [
            (1, 0),
            (-1, 0),
            (0, 1),
            (0, -1)
        ]

        while open_set:
            _, current_cost, current = heapq.heappop(open_set)

            if current == goal:
                path = [current]

                while current in came_from:
                    current = came_from[current]
                    path.append(current)

                path.reverse()
                return path

            for dx, dy in directions:
                neighbor = (current[0] + dx, current[1] + dy)

                if not is_valid(neighbor):
                    continue

                tentative_g_score = current_cost + 1

                if tentative_g_score < g_score.get(neighbor, float("inf")):
                    came_from[neighbor] = current
                    g_score[neighbor] = tentative_g_score

                    f_score = tentative_g_score + heuristic(neighbor, goal)

                    heapq.heappush(
                        open_set,
                        (f_score, tentative_g_score, neighbor)
                    )

        return []