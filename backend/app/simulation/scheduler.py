from __future__ import annotations
from enum import Enum
from typing import Dict, List, Optional, Tuple

from app.simulation.grid import Position
from app.simulation.robot import Robot, RobotState
from app.simulation.task import Task, TaskStatus
from app.simulation.pathfinding import a_star


class SchedulingPolicy(str, Enum):
    FIFO = "FIFO"
    NEAREST_ROBOT = "NEAREST_ROBOT"


class BaseScheduler:
    def assign_tasks(self, engine: "SimulationEngine") -> List[Tuple[str, str]]:
        """
        Returns list of (task_id, robot_id) assignments made.
        """
        raise NotImplementedError


class FIFOScheduler(BaseScheduler):
    """
    First-In, First-Out (FIFO) Task Scheduling.
    Orders pending tasks by creation tick ascending.
    Assigns the oldest task to the first available IDLE robot (sorted by ID for determinism).
    """
    def assign_tasks(self, engine: "SimulationEngine") -> List[Tuple[str, str]]:
        assignments: List[Tuple[str, str]] = []
        
        # Get pending tasks sorted by creation tick, then ID
        pending_tasks = [
            t for t in engine.tasks.values()
            if t.status == TaskStatus.PENDING
        ]
        pending_tasks.sort(key=lambda t: (t.created_at_tick, t.id))

        # Get idle robots sorted by ID
        idle_robots = [
            r for r in engine.robots.values()
            if r.status in (RobotState.IDLE, RobotState.WAITING) and r.task_id is None
        ]
        idle_robots.sort(key=lambda r: r.id)

        robot_idx = 0
        for task in pending_tasks:
            if robot_idx >= len(idle_robots):
                break
            robot = idle_robots[robot_idx]
            if engine.assign_task_to_robot(task.id, robot.id):
                assignments.append((task.id, robot.id))
                robot_idx += 1

        return assignments


class NearestRobotScheduler(BaseScheduler):
    """
    Nearest Available Robot Scheduling.
    Calculates shortest-path distance using A* from each idle robot to task pickup location.
    Assigns the task to the robot with lowest route distance, breaking ties deterministically.
    """
    def assign_tasks(self, engine: "SimulationEngine") -> List[Tuple[str, str]]:
        assignments: List[Tuple[str, str]] = []

        pending_tasks = [
            t for t in engine.tasks.values()
            if t.status == TaskStatus.PENDING
        ]
        # High priority tasks first, then older tasks
        priority_weights = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
        pending_tasks.sort(key=lambda t: (priority_weights.get(t.priority.value, 2), t.created_at_tick, t.id))

        available_robots = [
            r for r in engine.robots.values()
            if r.status in (RobotState.IDLE, RobotState.WAITING) and r.task_id is None
        ]

        for task in pending_tasks:
            if not available_robots:
                break

            # Find closest robot using A* shortest path distance
            best_robot: Optional[Robot] = None
            best_distance = float("inf")

            for robot in available_robots:
                # Calculate actual topological route cost
                path_res = a_star(engine.grid, robot.position, task.pickup_location)
                if path_res.found:
                    dist = path_res.cost
                else:
                    dist = float("inf")

                if dist < best_distance:
                    best_distance = dist
                    best_robot = robot
                elif dist == best_distance and best_robot is not None:
                    # Deterministic tie break by robot ID
                    if robot.id < best_robot.id:
                        best_robot = robot

            if best_robot is not None and best_distance < float("inf"):
                if engine.assign_task_to_robot(task.id, best_robot.id):
                    assignments.append((task.id, best_robot.id))
                    available_robots.remove(best_robot)

        return assignments


def get_scheduler(policy: SchedulingPolicy) -> BaseScheduler:
    if policy == SchedulingPolicy.FIFO:
        return FIFOScheduler()
    elif policy == SchedulingPolicy.NEAREST_ROBOT:
        return NearestRobotScheduler()
    return FIFOScheduler()
