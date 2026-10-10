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
        """Initializes warehouse layout matching the digital twin visual canvas."""
        # Charging docks in Charging Bay (bottom-left green area)
        charger_y = self.height - 2
        for x in range(1, min(5, self.width)):
            self.charging_stations.add((x, charger_y))
            
        # Workstations in Packing Station area (bottom-right blue area)
        dropoff_y = self.height - 3
        dropoff_cols = [15, 16, 17] if self.width >= 18 else [min(self.width - 2, 7)]
        for x in dropoff_cols:
            self.dropoff_stations.add((x, dropoff_y))
            
        # Storage shelves in central columns (rows 3 to 9 on standard 20x15)
        # Accurately matches digital twin canvas: Shelf A (6,7), Shelf B (9,10), Shelf C (12,13), Shelf D (15,16)
        shelf_cols = [6, 7, 9, 10, 12, 13, 15, 16] if self.width >= 18 else [x for x in [6, 7, 9] if x < self.width]
        for y in range(3, min(10, self.height - 3)):
            for x in shelf_cols:
                self.shelves.add((x, y))
                self.blocked_cells.add((x, y))

        # Restricted Zone (no entry hazard zone: x=7..12, y=11..14 on standard 20x15)
        if self.width >= 20 and self.height >= 15:
            for y in range(11, 15):
                for x in range(7, 13):
                    self.blocked_cells.add((x, y))

    def is_walkable(self, x: int, y: int) -> bool:
        """Check if a coordinate is within bounds and not blocked by static obstacles."""
        if not (0 <= x < self.width and 0 <= y < self.height):
            return False
        return (x, y) not in self.blocked_cells
