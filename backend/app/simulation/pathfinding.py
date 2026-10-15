from __future__ import annotations
import heapq
from collections import deque
from typing import Dict, List, Optional, Set, Tuple
from pydantic import BaseModel

from app.simulation.grid import GridMap, Position


class PathResult(BaseModel):
    path: List[Position]
    cost: int
    nodes_expanded: int
    found: bool
    algorithm: str = "A*"


def manhattan_heuristic(a: Position, b: Position) -> int:
    """Manhattan distance heuristic: h(n) = |x_a - x_b| + |y_a - y_b|"""
    return abs(a.x - b.x) + abs(a.y - b.y)


def a_star(
    grid: GridMap,
    start: Position,
    goal: Position,
    forbidden_positions: Optional[Set[Position]] = None,
    allow_goal_occupied: bool = False,
) -> PathResult:
    """
    A* algorithm implementation for uniform 4-directional grid graphs.
    
    Features:
    - Admissible & consistent Manhattan distance heuristic
    - Priority queue using Python heapq with deterministic tie-breaking
    - Start & goal validation
    - Support for temporary forbidden coordinates (dynamic collision reservations)
    - Reconstructs path and counts expanded nodes
    """
    # 1. Validation checks
    if not grid.is_inside(start):
        return PathResult(path=[], cost=0, nodes_expanded=0, found=False)
    if not grid.is_inside(goal):
        return PathResult(path=[], cost=0, nodes_expanded=0, found=False)
    
    if not grid.is_walkable(start, ignore_dynamic=False):
        return PathResult(path=[], cost=0, nodes_expanded=0, found=False)
    
    if not allow_goal_occupied and not grid.is_walkable(goal, ignore_dynamic=False):
        return PathResult(path=[], cost=0, nodes_expanded=0, found=False)

    # 2. Start == Goal edge-case
    if start == goal:
        return PathResult(path=[start], cost=0, nodes_expanded=0, found=True)

    extra_forbidden = forbidden_positions or set()

    # Open set elements: (f_score, h_score, tie_breaker, current_pos)
    # Using tie_breaker ensures deterministic behavior when f and h match
    tie_breaker = 0
    open_heap: List[Tuple[int, int, int, Position]] = []
    start_h = manhattan_heuristic(start, goal)
    heapq.heappush(open_heap, (start_h, start_h, tie_breaker, start))

    came_from: Dict[Position, Position] = {}
    g_score: Dict[Position, int] = {start: 0}
    closed_set: Set[Position] = set()

    nodes_expanded = 0

    while open_heap:
        _, _, _, current = heapq.heappop(open_heap)

        if current in closed_set:
            continue
        closed_set.add(current)
        nodes_expanded += 1

        # Check goal reached
        if current == goal:
            # Reconstruct path
            path: List[Position] = [current]
            curr = current
            while curr in came_from:
                curr = came_from[curr]
                path.append(curr)
            path.reverse()
            return PathResult(
                path=path,
                cost=len(path) - 1,
                nodes_expanded=nodes_expanded,
                found=True,
                algorithm="A*",
            )

        # Explore 4-directional neighbors
        for neighbor in grid.neighbors(current):
            # If neighbor is forbidden (by reservation or dynamic barrier) and not the goal (if allow_goal_occupied)
            if neighbor in extra_forbidden and neighbor != goal:
                continue
            if neighbor in closed_set:
                continue

            tentative_g = g_score[current] + 1  # Uniform edge cost = 1

            if tentative_g < g_score.get(neighbor, float("inf")):
                came_from[neighbor] = current
                g_score[neighbor] = tentative_g
                h = manhattan_heuristic(neighbor, goal)
                f = tentative_g + h
                tie_breaker += 1
                heapq.heappush(open_heap, (f, h, tie_breaker, neighbor))

    # Path not found / goal unreachable
    return PathResult(path=[], cost=0, nodes_expanded=nodes_expanded, found=False)


def bfs_pathfinding(grid: GridMap, start: Position, goal: Position) -> PathResult:
    """
    Breadth-First Search (BFS) implementation for baseline comparison in unit tests.
    Guarantees shortest path length on unweighted graphs.
    """
    if not grid.is_inside(start) or not grid.is_inside(goal):
        return PathResult(path=[], cost=0, nodes_expanded=0, found=False, algorithm="BFS")
    if not grid.is_walkable(start) or not grid.is_walkable(goal):
        return PathResult(path=[], cost=0, nodes_expanded=0, found=False, algorithm="BFS")
    if start == goal:
        return PathResult(path=[start], cost=0, nodes_expanded=0, found=True, algorithm="BFS")

    queue = deque([start])
    came_from: Dict[Position, Position] = {}
    visited: Set[Position] = {start}
    nodes_expanded = 0

    while queue:
        current = queue.popleft()
        nodes_expanded += 1

        if current == goal:
            path: List[Position] = [current]
            curr = current
            while curr in came_from:
                curr = came_from[curr]
                path.append(curr)
            path.reverse()
            return PathResult(
                path=path,
                cost=len(path) - 1,
                nodes_expanded=nodes_expanded,
                found=True,
                algorithm="BFS",
            )

        for neighbor in grid.neighbors(current):
            if neighbor not in visited:
                visited.add(neighbor)
                came_from[neighbor] = current
                queue.append(neighbor)

    return PathResult(path=[], cost=0, nodes_expanded=nodes_expanded, found=False, algorithm="BFS")
