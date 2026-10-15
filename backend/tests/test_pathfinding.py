import pytest
from app.simulation.grid import CellType, GridMap, Position
from app.simulation.pathfinding import a_star, bfs_pathfinding, manhattan_heuristic


def test_manhattan_heuristic():
    p1 = Position(x=0, y=0)
    p2 = Position(x=3, y=4)
    assert manhattan_heuristic(p1, p2) == 7
    assert p1.manhattan_distance(p2) == 7


def test_start_equals_goal():
    grid = GridMap(width=10, height=10)
    pos = Position(x=5, y=5)
    res = a_star(grid, pos, pos)
    assert res.found is True
    assert res.cost == 0
    assert res.path == [pos]


def test_invalid_start_or_goal():
    grid = GridMap(width=5, height=5)
    # Outside map
    out = Position(x=-1, y=2)
    valid = Position(x=2, y=2)
    assert a_star(grid, out, valid).found is False
    assert a_star(grid, valid, out).found is False

    # Obstacle as start or goal
    grid.set_cell_type(Position(x=1, y=1), CellType.WALL)
    assert a_star(grid, Position(x=1, y=1), valid).found is False
    assert a_star(grid, valid, Position(x=1, y=1)).found is False


def test_direct_path():
    grid = GridMap(width=10, height=10)
    start = Position(x=1, y=1)
    goal = Position(x=1, y=5)
    res = a_star(grid, start, goal)
    
    assert res.found is True
    assert res.cost == 4
    assert len(res.path) == 5
    assert res.path[0] == start
    assert res.path[-1] == goal
    # Path should be straight down: (1,1) -> (1,2) -> (1,3) -> (1,4) -> (1,5)
    expected = [Position(x=1, y=y) for y in range(1, 6)]
    assert res.path == expected


def test_path_around_obstacle():
    grid = GridMap(width=10, height=10)
    start = Position(x=2, y=5)
    goal = Position(x=6, y=5)
    
    # Build a vertical wall between x=4, y=3..7
    for y in range(3, 8):
        grid.set_cell_type(Position(x=4, y=y), CellType.WALL)
        
    res = a_star(grid, start, goal)
    assert res.found is True
    # Ensure no node in path crosses the wall
    for p in res.path:
        assert not (p.x == 4 and 3 <= p.y <= 7), f"Path illegally traversed obstacle at {p}"
    
    assert res.path[0] == start
    assert res.path[-1] == goal


def test_unreachable_destination():
    grid = GridMap(width=10, height=10)
    start = Position(x=1, y=1)
    goal = Position(x=5, y=5)
    
    # Completely box in goal at (5,5) with walls:
    # (4,5), (6,5), (5,4), (5,6)
    grid.set_cell_type(Position(x=4, y=5), CellType.WALL)
    grid.set_cell_type(Position(x=6, y=5), CellType.WALL)
    grid.set_cell_type(Position(x=5, y=4), CellType.WALL)
    grid.set_cell_type(Position(x=5, y=6), CellType.WALL)
    
    res = a_star(grid, start, goal)
    assert res.found is False
    assert res.path == []


def test_disconnected_map():
    grid = GridMap(width=10, height=10)
    start = Position(x=1, y=5)
    goal = Position(x=8, y=5)
    
    # Full vertical wall dividing the map
    for y in range(10):
        grid.set_cell_type(Position(x=5, y=y), CellType.WALL)
        
    res = a_star(grid, start, goal)
    assert res.found is False
    assert res.cost == 0


def test_compare_path_length_against_bfs():
    """
    On a uniform 4-directional grid with obstacles, A* with an admissible
    Manhattan heuristic must yield an optimal path whose length equals BFS.
    """
    grid = GridMap.create_default_factory()
    start = Position(x=1, y=2)   # Pickup station A
    goal = Position(x=18, y=10)  # Bay Out 3
    
    astar_res = a_star(grid, start, goal)
    bfs_res = bfs_pathfinding(grid, start, goal)
    
    assert astar_res.found is True
    assert bfs_res.found is True
    assert astar_res.cost == bfs_res.cost
    assert len(astar_res.path) == len(bfs_res.path)
    
    # A* should expand fewer or equal nodes than unguided BFS
    assert astar_res.nodes_expanded <= bfs_res.nodes_expanded


def test_forbidden_positions_support():
    grid = GridMap(width=5, height=5)
    start = Position(x=0, y=0)
    goal = Position(x=2, y=0)
    
    # (1,0) is walkable on grid, but temporarily forbidden
    forbidden = {Position(x=1, y=0)}
    res = a_star(grid, start, goal, forbidden_positions=forbidden)
    
    assert res.found is True
    assert Position(x=1, y=0) not in res.path
    assert res.cost > 2  # Has to route around (0,0)->(0,1)->(1,1)->(2,1)->(2,0)
