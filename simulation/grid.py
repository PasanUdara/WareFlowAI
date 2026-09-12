"""
Warehouse Grid Map [Member 2]
Defines 2D coordinates for aisles, storage shelves, charging stations, and drop-off stations.
"""

from typing import List, Tuple, Set


class WarehouseGrid:
    """
    2D coordinate system representing the warehouse floor.
    """
    
    def __init__(self, width: int = 20, height: int = 15):
        self.width = width
        self.height = height
        self.shelves: Set[Tuple[int, int]] = set()
        self.charging_stations: Set[Tuple[int, int]] = set()
        self.dropoff_stations: Set[Tuple[int, int]] = set()
        self.blocked_cells: Set[Tuple[int, int]] = set()
        self._setup_layout()
        
    def _setup_layout(self):
        """Initializes default warehouse layout."""
        # Charging docks along top wall
        for x in range(1, 5):
            self.charging_stations.add((x, 0))
            
        # Workstations along bottom wall
        for x in range(1, 5):
            self.dropoff_stations.add((x, self.height - 1))
            
        # Storage shelves in central columns
        for y in range(3, self.height - 3):
            for x in [4, 5, 8, 9, 12, 13, 16, 17]:
                self.shelves.add((x, y))
                self.blocked_cells.add((x, y))

    def is_walkable(self, x: int, y: int) -> bool:
        """Check if a coordinate is within bounds and not blocked by static obstacles."""
        if not (0 <= x < self.width and 0 <= y < self.height):
            return False
        return (x, y) not in self.blocked_cells
