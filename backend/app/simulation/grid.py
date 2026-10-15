from __future__ import annotations
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple
from pydantic import BaseModel, Field


class CellType(str, Enum):
    FREE = "FREE"
    WALL = "WALL"
    SHELF = "SHELF"
    WORKSTATION = "WORKSTATION"
    PICKUP = "PICKUP"
    DELIVERY = "DELIVERY"
    INSPECTION = "INSPECTION"
    CHARGING = "CHARGING"
    OBSTACLE = "OBSTACLE"  # Dynamic blockage


class Position(BaseModel):
    x: int
    y: int

    def __hash__(self) -> int:
        return hash((self.x, self.y))

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Position):
            return self.x == other.x and self.y == other.y
        if isinstance(other, (tuple, list)) and len(other) == 2:
            return self.x == other[0] and self.y == other[1]
        return False

    def manhattan_distance(self, other: Position) -> int:
        return abs(self.x - other.x) + abs(self.y - other.y)

    def to_tuple(self) -> Tuple[int, int]:
        return (self.x, self.y)

    @classmethod
    def from_tuple(cls, t: Tuple[int, int]) -> Position:
        return cls(x=t[0], y=t[1])


class DynamicObstacle(BaseModel):
    id: str
    position: Position
    created_at_tick: int
    duration_ticks: Optional[int] = None  # None = permanent until removed


class GridMap:
    def __init__(self, width: int = 20, height: int = 15):
        self.width = width
        self.height = height
        self.static_obstacles: Set[Position] = set()
        self.cell_types: Dict[Position, CellType] = {}
        
        # Designated stations
        self.workstations: Dict[str, Position] = {}
        self.pickup_stations: Dict[str, Position] = {}
        self.delivery_stations: Dict[str, Position] = {}
        self.inspection_stations: Dict[str, Position] = {}
        self.charging_stations: Dict[str, Position] = {}
        
        # Dynamic blockages
        self.dynamic_obstacles: Dict[str, DynamicObstacle] = {}

    def is_inside(self, pos: Position) -> bool:
        return 0 <= pos.x < self.width and 0 <= pos.y < self.height

    def is_walkable(self, pos: Position, ignore_dynamic: bool = False) -> bool:
        if not self.is_inside(pos):
            return False
        if pos in self.static_obstacles:
            return False
        if not ignore_dynamic:
            for obs in self.dynamic_obstacles.values():
                if obs.position == pos:
                    return False
        return True

    def set_cell_type(self, pos: Position, cell_type: CellType) -> None:
        if not self.is_inside(pos):
            raise ValueError(f"Position {pos} outside map bounds ({self.width}x{self.height})")
        self.cell_types[pos] = cell_type
        if cell_type in (CellType.WALL, CellType.SHELF):
            self.static_obstacles.add(pos)
        else:
            self.static_obstacles.discard(pos)

    def add_workstation(self, name: str, pos: Position) -> None:
        self.set_cell_type(pos, CellType.WORKSTATION)
        self.workstations[name] = pos

    def add_pickup_station(self, name: str, pos: Position) -> None:
        self.set_cell_type(pos, CellType.PICKUP)
        self.pickup_stations[name] = pos

    def add_delivery_station(self, name: str, pos: Position) -> None:
        self.set_cell_type(pos, CellType.DELIVERY)
        self.delivery_stations[name] = pos

    def add_inspection_station(self, name: str, pos: Position) -> None:
        self.set_cell_type(pos, CellType.INSPECTION)
        self.inspection_stations[name] = pos

    def add_charging_station(self, name: str, pos: Position) -> None:
        self.set_cell_type(pos, CellType.CHARGING)
        self.charging_stations[name] = pos

    def add_dynamic_obstacle(self, obstacle_id: str, pos: Position, tick: int = 0, duration: Optional[int] = None) -> bool:
        if not self.is_inside(pos):
            return False
        if pos in self.static_obstacles:
            return False  # Already blocked by wall/shelf
        self.dynamic_obstacles[obstacle_id] = DynamicObstacle(
            id=obstacle_id,
            position=pos,
            created_at_tick=tick,
            duration_ticks=duration
        )
        return True

    def remove_dynamic_obstacle(self, obstacle_id: str) -> bool:
        if obstacle_id in self.dynamic_obstacles:
            del self.dynamic_obstacles[obstacle_id]
            return True
        return False

    def neighbors(self, pos: Position) -> List[Position]:
        """Returns 4-directional walkable neighbors (Up, Right, Down, Left)."""
        candidates = [
            Position(x=pos.x, y=pos.y - 1),  # North
            Position(x=pos.x + 1, y=pos.y),  # East
            Position(x=pos.x, y=pos.y + 1),  # South
            Position(x=pos.x - 1, y=pos.y),  # West
        ]
        return [p for p in candidates if self.is_walkable(p)]

    def to_dict(self) -> dict:
        return {
            "width": self.width,
            "height": self.height,
            "static_obstacles": [{"x": p.x, "y": p.y} for p in sorted(self.static_obstacles, key=lambda p: (p.x, p.y))],
            "cell_types": {f"{p.x},{p.y}": t.value for p, t in self.cell_types.items()},
            "workstations": {k: {"x": v.x, "y": v.y} for k, v in self.workstations.items()},
            "pickup_stations": {k: {"x": v.x, "y": v.y} for k, v in self.pickup_stations.items()},
            "delivery_stations": {k: {"x": v.x, "y": v.y} for k, v in self.delivery_stations.items()},
            "inspection_stations": {k: {"x": v.x, "y": v.y} for k, v in self.inspection_stations.items()},
            "charging_stations": {k: {"x": v.x, "y": v.y} for k, v in self.charging_stations.items()},
            "dynamic_obstacles": [
                {
                    "id": obs.id,
                    "x": obs.position.x,
                    "y": obs.position.y,
                    "created_at_tick": obs.created_at_tick,
                    "duration_ticks": obs.duration_ticks,
                }
                for obs in self.dynamic_obstacles.values()
            ],
        }

    @classmethod
    def create_default_factory(cls) -> GridMap:
        """
        Creates a realistic 20x15 factory floor with:
        - Outer perimeter buffer
        - Warehouse storage shelves with navigation aisles
        - Assembly & packing workstations
        - Material pickup depot (P1, P2)
        - Finished goods delivery depot (D1, D2)
        - Dedicated AI Visual Quality Inspection station (I1)
        - Fleet charging & staging docks (C1, C2, C3)
        """
        grid = cls(width=20, height=15)

        # Storage shelving racks (Aisle 1 & 2)
        # Shelves at (3..6, 3), (3..6, 7), (13..16, 3), (13..16, 7)
        for x in range(3, 7):
            grid.set_cell_type(Position(x=x, y=3), CellType.SHELF)
            grid.set_cell_type(Position(x=x, y=4), CellType.SHELF)
            grid.set_cell_type(Position(x=x, y=7), CellType.SHELF)
            grid.set_cell_type(Position(x=x, y=8), CellType.SHELF)

        for x in range(13, 17):
            grid.set_cell_type(Position(x=x, y=3), CellType.SHELF)
            grid.set_cell_type(Position(x=x, y=4), CellType.SHELF)
            grid.set_cell_type(Position(x=x, y=7), CellType.SHELF)
            grid.set_cell_type(Position(x=x, y=8), CellType.SHELF)

        # Workstations along the middle corridor
        grid.add_workstation("WS_ASSEMBLY_1", Position(x=9, y=3))
        grid.add_workstation("WS_ASSEMBLY_2", Position(x=10, y=3))
        grid.add_workstation("WS_PACKING_1", Position(x=9, y=8))
        grid.add_workstation("WS_PACKING_2", Position(x=10, y=8))

        # Pickup points (raw materials intake)
        grid.add_pickup_station("PICKUP_A", Position(x=1, y=2))
        grid.add_pickup_station("PICKUP_B", Position(x=1, y=6))
        grid.add_pickup_station("PICKUP_C", Position(x=1, y=10))

        # Delivery points (shipping staging bays)
        grid.add_delivery_station("BAY_OUT_1", Position(x=18, y=2))
        grid.add_delivery_station("BAY_OUT_2", Position(x=18, y=6))
        grid.add_delivery_station("BAY_OUT_3", Position(x=18, y=10))

        # Quality Inspection Station
        grid.add_inspection_station("QC_INSPECTION_1", Position(x=10, y=12))

        # Charging pads (fleet staging docks at bottom)
        grid.add_charging_station("DOCK_1", Position(x=4, y=13))
        grid.add_charging_station("DOCK_2", Position(x=6, y=13))
        grid.add_charging_station("DOCK_3", Position(x=14, y=13))
        grid.add_charging_station("DOCK_4", Position(x=16, y=13))

        return grid
