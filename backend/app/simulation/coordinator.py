from __future__ import annotations
from typing import Dict, List, Optional, Set, Tuple
from app.simulation.grid import GridMap, Position
from app.simulation.robot import Robot, RobotState
from app.simulation.pathfinding import a_star


class ConflictResolution(str):
    MOVE_APPROVED = "APPROVED"
    WAIT_YIELDED = "WAIT_YIELDED"
    EDGE_SWAP_REJECTED = "EDGE_SWAP_REJECTED"
    VERTEX_CONFLICT_REJECTED = "VERTEX_CONFLICT_REJECTED"
    OBSTACLE_BLOCKED = "OBSTACLE_BLOCKED"


class MovementCoordinator:
    """
    Centralized movement coordinator for safe multi-robot fleet navigation.
    
    Guarantees:
    1. No simultaneous vertex occupancy (two robots in same cell).
    2. No head-on edge swaps (robot A moving to B while B moves to A).
    3. Deterministic priority ordering (task priority, then robot ID).
    4. Bounded waiting before triggering dynamic route replanning around blockers.
    """
    def __init__(self, max_wait_before_replan: int = 2):
        self.max_wait_before_replan = max_wait_before_replan
        self.consecutive_waits: Dict[str, int] = {}

    def get_robot_priority(self, robot: Robot) -> Tuple[int, str]:
        """
        Higher priority value goes first.
        Priority:
        3: INSPECTING / critical task
        2: MOVING with task
        1: MOVING without task
        0: IDLE / WAITING
        Tie-breaker: Reverse robot_id for deterministic ordering.
        """
        state_weight = 0
        if robot.status == RobotState.INSPECTING:
            state_weight = 3
        elif robot.task_id and robot.status == RobotState.MOVING:
            state_weight = 2
        elif robot.status == RobotState.MOVING:
            state_weight = 1
        return (state_weight, robot.id)

    def coordinate_step(
        self,
        grid: GridMap,
        robots: Dict[str, Robot],
    ) -> Dict[str, Tuple[ConflictResolution, Optional[Position]]]:
        """
        Calculates approved moves and required waits/replans for all robots.
        Returns mapping: robot_id -> (ConflictResolution, approved_next_position)
        """
        results: Dict[str, Tuple[ConflictResolution, Optional[Position]]] = {}

        # 1. Identify intent for each robot
        desired_moves: Dict[str, Position] = {}
        for r_id, robot in robots.items():
            if robot.status == RobotState.MOVING and robot.planned_path:
                next_idx = robot.path_index + 1
                if next_idx < len(robot.planned_path):
                    desired_moves[r_id] = robot.planned_path[next_idx]
                else:
                    desired_moves[r_id] = robot.position
            else:
                desired_moves[r_id] = robot.position

        # 2. Sort robots by priority descending
        sorted_robots = sorted(
            robots.values(),
            key=lambda r: self.get_robot_priority(r),
            reverse=True,
        )

        reserved_cells_for_next_tick: Dict[Position, str] = {}
        
        # 3. Reserve cells for robots that are stationary or faulted
        for robot in sorted_robots:
            r_id = robot.id
            if r_id not in desired_moves or desired_moves[r_id] == robot.position:
                reserved_cells_for_next_tick[robot.position] = r_id
                results[r_id] = (ConflictResolution.MOVE_APPROVED, robot.position)

        # 4. Resolve moving robots in priority order
        for robot in sorted_robots:
            r_id = robot.id
            if r_id in results:
                continue  # already marked stationary

            curr_pos = robot.position
            desired_pos = desired_moves[r_id]

            # Rule A: Check obstacle
            if not grid.is_walkable(desired_pos):
                results[r_id] = (ConflictResolution.OBSTACLE_BLOCKED, curr_pos)
                reserved_cells_for_next_tick[curr_pos] = r_id
                continue

            # Rule B: Edge-swap check against other robots
            edge_conflict = False
            for other_id, other_robot in robots.items():
                if other_id != r_id:
                    other_curr = other_robot.position
                    other_desired = desired_moves.get(other_id, other_curr)
                    if desired_pos == other_curr and other_desired == curr_pos:
                        edge_conflict = True
                        break

            if edge_conflict:
                results[r_id] = (ConflictResolution.EDGE_SWAP_REJECTED, curr_pos)
                reserved_cells_for_next_tick[curr_pos] = r_id
                continue

            # Rule C: Vertex conflict check
            if desired_pos in reserved_cells_for_next_tick:
                # Cell already claimed by higher-priority robot
                results[r_id] = (ConflictResolution.VERTEX_CONFLICT_REJECTED, curr_pos)
                reserved_cells_for_next_tick[curr_pos] = r_id
                continue

            # Approved!
            reserved_cells_for_next_tick[desired_pos] = r_id
            results[r_id] = (ConflictResolution.MOVE_APPROVED, desired_pos)
            self.consecutive_waits[r_id] = 0

        # Update wait counts for robots that yielded
        for r_id, (res, _) in results.items():
            if res in (
                ConflictResolution.EDGE_SWAP_REJECTED,
                ConflictResolution.VERTEX_CONFLICT_REJECTED,
                ConflictResolution.OBSTACLE_BLOCKED,
            ):
                self.consecutive_waits[r_id] = self.consecutive_waits.get(r_id, 0) + 1

        return results

    def should_replan(self, robot_id: str) -> bool:
        return self.consecutive_waits.get(robot_id, 0) >= self.max_wait_before_replan
