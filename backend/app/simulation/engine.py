from __future__ import annotations
import copy
from typing import Callable, Dict, List, Optional, Set, Tuple
from pydantic import BaseModel, Field

from app.simulation.grid import CellType, GridMap, Position
from app.simulation.robot import Robot, RobotState
from app.simulation.pathfinding import a_star, PathResult
from app.simulation.task import Task, TaskPriority, TaskStatus
from app.simulation.coordinator import MovementCoordinator, ConflictResolution
from app.simulation.scheduler import SchedulingPolicy, BaseScheduler, get_scheduler


class SimulationMetrics(BaseModel):
    total_ticks: int = 0
    tasks_created: int = 0
    tasks_completed: int = 0
    tasks_failed: int = 0
    total_distance_travelled: int = 0
    total_wait_ticks: int = 0
    replans_count: int = 0
    conflicts_prevented: int = 0
    actual_collisions: int = 0  # Expected to be 0 at all times
    throughput_per_100_ticks: float = 0.0
    avg_delivery_time_ticks: float = 0.0


class SimulationEvent(BaseModel):
    tick: int
    event_type: str
    message: str
    data: dict = Field(default_factory=dict)


class SimulationEngine:
    def __init__(
        self,
        grid: Optional[GridMap] = None,
        random_seed: int = 42,
        scheduling_policy: SchedulingPolicy = SchedulingPolicy.NEAREST_ROBOT,
    ):
        if isinstance(scheduling_policy, str):
            scheduling_policy = SchedulingPolicy(scheduling_policy)
        self.grid = grid or GridMap.create_default_factory()
        self.robots: Dict[str, Robot] = {}
        self.tasks: Dict[str, Task] = {}
        self.robot_task_stage: Dict[str, str] = {}  # robot_id -> "PICKUP" or "DELIVERY"
        self.coordinator = MovementCoordinator(max_wait_before_replan=2)
        self.scheduling_policy = scheduling_policy
        self.scheduler: BaseScheduler = get_scheduler(scheduling_policy)
        self.tick: int = 0
        self.is_running: bool = False
        self.events: List[SimulationEvent] = []
        self.metrics = SimulationMetrics()
        self.random_seed = random_seed
        self.event_callbacks: List[Callable[[SimulationEvent], None]] = []

    def set_scheduling_policy(self, policy: SchedulingPolicy) -> None:
        if isinstance(policy, str):
            policy = SchedulingPolicy(policy)
        self.scheduling_policy = policy
        self.scheduler = get_scheduler(policy)
        policy_str = policy.value if hasattr(policy, "value") else str(policy)
        self.emit_event(
            "scheduler.policy_changed",
            f"Scheduling policy updated to {policy_str}",
            {"policy": policy_str},
        )

    def register_event_listener(self, callback: Callable[[SimulationEvent], None]) -> None:
        self.event_callbacks.append(callback)

    def emit_event(self, event_type: str, message: str, data: Optional[dict] = None) -> SimulationEvent:
        event = SimulationEvent(
            tick=self.tick,
            event_type=event_type,
            message=message,
            data=data or {},
        )
        self.events.append(event)
        for cb in self.event_callbacks:
            try:
                cb(event)
            except Exception:
                pass
        return event

    def add_robot(self, robot_id: str, initial_position: Position) -> Robot:
        if not self.grid.is_walkable(initial_position):
            raise ValueError(f"Initial position {initial_position} is not walkable")
        if robot_id in self.robots:
            raise ValueError(f"Robot {robot_id} already exists")

        robot = Robot(id=robot_id, position=initial_position)
        self.robots[robot_id] = robot
        self.emit_event(
            "robot.added",
            f"Robot {robot_id} initialized at ({initial_position.x}, {initial_position.y})",
            {"robot_id": robot_id, "position": initial_position.to_tuple()},
        )
        return robot

    def add_task(self, task: Task) -> None:
        self.tasks[task.id] = task
        self.metrics.tasks_created += 1
        self.emit_event(
            "task.created",
            f"Task {task.id} created from {task.pickup_location.to_tuple()} to {task.destination.to_tuple()}",
            {"task_id": task.id, "priority": task.priority.value},
        )

    def assign_task_to_robot(self, task_id: str, robot_id: str) -> bool:
        task = self.tasks.get(task_id)
        robot = self.robots.get(robot_id)
        if not task or not robot:
            return False
        if robot.status not in (RobotState.IDLE, RobotState.WAITING):
            return False

        task.mark_assigned(robot_id)
        robot.task_id = task_id
        self.robot_task_stage[robot_id] = "PICKUP"

        # Plan route to pickup station
        plan_result = a_star(self.grid, robot.position, task.pickup_location)
        if plan_result.found:
            robot.assign_path(plan_result.path, task.pickup_location, task_id=task_id)
            self.emit_event(
                "task.assigned",
                f"Task {task_id} assigned to robot {robot_id}; en route to pickup",
                {"task_id": task_id, "robot_id": robot_id, "cost": plan_result.cost},
            )
            return True
        else:
            task.mark_failed(f"No reachable path from robot {robot_id} to pickup {task.pickup_location.to_tuple()}")
            robot.task_id = None
            self.metrics.tasks_failed += 1
            return False

    def plan_route_for_robot(
        self,
        robot_id: str,
        destination: Position,
        avoid_other_robots: bool = False,
    ) -> bool:
        robot = self.robots.get(robot_id)
        if not robot:
            return False

        forbidden = set()
        if avoid_other_robots:
            forbidden = {
                r.position for other_id, r in self.robots.items()
                if other_id != robot_id
            }

        result = a_star(self.grid, robot.position, destination, forbidden_positions=forbidden)
        if result.found:
            robot.assign_path(result.path, destination)
            self.emit_event(
                "robot.path_planned",
                f"Path planned for {robot_id}: cost {result.cost}, nodes expanded {result.nodes_expanded}",
                {"robot_id": robot_id, "destination": destination.to_tuple(), "cost": result.cost},
            )
            return True
        else:
            self.emit_event(
                "robot.planning_failed",
                f"No reachable path found for {robot_id} to destination {destination.to_tuple()}",
                {"robot_id": robot_id, "destination": destination.to_tuple()},
            )
            return False

    def add_dynamic_obstacle(self, obstacle_id: str, pos: Position, duration: Optional[int] = None) -> bool:
        success = self.grid.add_dynamic_obstacle(obstacle_id, pos, tick=self.tick, duration=duration)
        if success:
            self.emit_event(
                "obstacle.added",
                f"Dynamic obstacle {obstacle_id} placed at {pos.to_tuple()}",
                {"obstacle_id": obstacle_id, "position": pos.to_tuple()},
            )
            # Check affected robots and trigger replanning if obstacle is in planned path
            for r_id, robot in self.robots.items():
                if robot.status == RobotState.MOVING and pos in robot.planned_path:
                    self.emit_event(
                        "robot.path_invalidated",
                        f"Robot {r_id} path invalidated by obstacle at {pos.to_tuple()}",
                        {"robot_id": r_id, "obstacle_id": obstacle_id},
                    )
                    self.attempt_replanning(r_id)
        return success

    def remove_dynamic_obstacle(self, obstacle_id: str) -> bool:
        success = self.grid.remove_dynamic_obstacle(obstacle_id)
        if success:
            self.emit_event(
                "obstacle.removed",
                f"Dynamic obstacle {obstacle_id} removed",
                {"obstacle_id": obstacle_id},
            )
        return success

    def attempt_replanning(self, robot_id: str) -> bool:
        robot = self.robots.get(robot_id)
        if not robot or not robot.destination:
            return False

        self.metrics.replans_count += 1
        other_positions = {r.position for oid, r in self.robots.items() if oid != robot_id}

        result = a_star(self.grid, robot.position, robot.destination, forbidden_positions=other_positions)
        if result.found:
            robot.assign_path(result.path, robot.destination, task_id=robot.task_id)
            self.coordinator.consecutive_waits[robot_id] = 0
            self.emit_event(
                "robot.replanned",
                f"Robot {robot_id} successfully replanned new route (cost: {result.cost})",
                {"robot_id": robot_id, "new_cost": result.cost},
            )
            return True
        else:
            robot.record_wait_tick()
            self.emit_event(
                "robot.wait_no_route",
                f"Robot {robot_id} waiting: no alternative route currently available",
                {"robot_id": robot_id},
            )
            return False

    def trigger_robot_fault(self, robot_id: str, reason: str = "Tire slippage / Motor error") -> bool:
        robot = self.robots.get(robot_id)
        if not robot:
            return False

        robot.trigger_fault(reason)
        self.emit_event(
            "robot.faulted",
            f"Robot {robot_id} faulted: {reason}",
            {"robot_id": robot_id, "reason": reason, "task_id": robot.task_id},
        )

        # Recover task if assigned
        if robot.task_id and robot.task_id in self.tasks:
            task = self.tasks[robot.task_id]
            task.mark_failed(f"Robot {robot_id} faulted during execution: {reason}")
            self.metrics.tasks_failed += 1
            robot.task_id = None
            self.emit_event(
                "task.reassignment_needed",
                f"Task {task.id} released due to robot {robot_id} fault",
                {"task_id": task.id},
            )
        return True

    def recover_robot(self, robot_id: str) -> bool:
        robot = self.robots.get(robot_id)
        if not robot or robot.status != RobotState.FAULTED:
            return False

        robot.recover_from_fault()
        self.emit_event(
            "robot.recovered",
            f"Robot {robot_id} recovered from fault and is now IDLE",
            {"robot_id": robot_id},
        )
        return True

    def step(self) -> None:
        """
        Advances the simulation clock by 1 discrete tick deterministically.
        Coordinates robot movements, handles conflict resolution, replanning,
        and task transitions.
        """
        self.tick += 1
        self.metrics.total_ticks = self.tick

        # Automatically assign pending tasks using the active policy
        self.scheduler.assign_tasks(self)

        # Coordinate movements using centralized coordinator
        coordination_results = self.coordinator.coordinate_step(self.grid, self.robots)

        for r_id, (decision, target_pos) in coordination_results.items():
            robot = self.robots[r_id]

            if decision == ConflictResolution.MOVE_APPROVED:
                if target_pos != robot.position:
                    robot.step_along_path()
                    self.metrics.total_distance_travelled += 1

                    # Check task waypoint arrivals
                    self._check_task_progression(robot)

            elif decision in (
                ConflictResolution.EDGE_SWAP_REJECTED,
                ConflictResolution.VERTEX_CONFLICT_REJECTED,
            ):
                robot.record_wait_tick()
                self.metrics.total_wait_ticks += 1
                self.metrics.conflicts_prevented += 1
                self.emit_event(
                    "conflict.prevented",
                    f"Coordinator prevented {decision} for robot {r_id} at {robot.position.to_tuple()}",
                    {"robot_id": r_id, "decision": decision},
                )

                if self.coordinator.should_replan(r_id):
                    self.attempt_replanning(r_id)

            elif decision == ConflictResolution.OBSTACLE_BLOCKED:
                robot.record_wait_tick()
                self.metrics.total_wait_ticks += 1
                self.metrics.conflicts_prevented += 1
                self.emit_event(
                    "movement.blocked_by_obstacle",
                    f"Robot {r_id} movement blocked by obstacle",
                    {"robot_id": r_id},
                )
                self.attempt_replanning(r_id)

        # Invariant check: Verify zero simultaneous cell occupancy
        occupied = [r.position for r in self.robots.values()]
        if len(occupied) != len(set(occupied)):
            self.metrics.actual_collisions += 1
            self.emit_event("collision.detected", "CRITICAL INVARIANT VIOLATION: Simultaneous occupancy detected!")

        # Update metrics
        if self.metrics.total_ticks > 0:
            self.metrics.throughput_per_100_ticks = (
                (self.metrics.tasks_completed / self.metrics.total_ticks) * 100.0
            )

    def _check_task_progression(self, robot: Robot) -> None:
        if not robot.task_id or robot.task_id not in self.tasks:
            return

        task = self.tasks[robot.task_id]
        stage = self.robot_task_stage.get(robot.id, "PICKUP")

        if stage == "PICKUP" and robot.position == task.pickup_location:
            # Reached pickup! Switch to DELIVERY
            task.status = TaskStatus.DELIVERING
            self.robot_task_stage[robot.id] = "DELIVERY"
            self.emit_event(
                "task.picked_up",
                f"Robot {robot.id} picked up task {task.id}; navigating to destination {task.destination.to_tuple()}",
                {"task_id": task.id, "robot_id": robot.id},
            )
            # Plan route to delivery destination
            other_positions = {r.position for oid, r in self.robots.items() if oid != robot.id}
            plan_res = a_star(self.grid, robot.position, task.destination, forbidden_positions=other_positions)
            if plan_res.found:
                robot.assign_path(plan_res.path, task.destination, task_id=task.id)
            else:
                robot.record_wait_tick()

        elif stage == "DELIVERY" and robot.position == task.destination:
            # Reached delivery location!
            if task.requires_inspection:
                task.status = TaskStatus.INSPECTION_PENDING
                robot.set_state(RobotState.INSPECTING)
                self.emit_event(
                    "inspection.queued",
                    f"Task {task.id} delivered to inspection station {task.destination.to_tuple()}; awaiting AI inspection",
                    {"task_id": task.id, "image_id": task.inspection_image_id},
                )
            else:
                task.mark_completed(self.tick)
                robot.tasks_completed += 1
                robot.set_state(RobotState.IDLE)
                robot.planned_path = []
                robot.path_index = 0
                robot.destination = None
                robot.task_id = None
                self.robot_task_stage.pop(robot.id, None)
                self.metrics.tasks_completed += 1
                self.emit_event(
                    "task.completed",
                    f"Task {task.id} completed by robot {robot.id} at tick {self.tick}",
                    {"task_id": task.id, "robot_id": robot.id, "duration": self.tick - task.created_at_tick},
                )

    def get_state(self) -> dict:
        return {
            "tick": self.tick,
            "is_running": self.is_running,
            "scheduling_policy": self.scheduling_policy.value if hasattr(self.scheduling_policy, "value") else str(self.scheduling_policy),
            "grid": self.grid.to_dict(),
            "robots": {r_id: r.model_dump() for r_id, r in self.robots.items()},
            "tasks": {t_id: t.model_dump() for t_id, t in self.tasks.items()},
            "metrics": self.metrics.model_dump(),
            "recent_events": [e.model_dump() for e in self.events[-20:]],
        }

    def reset(self) -> None:
        self.tick = 0
        self.is_running = False
        self.events.clear()
        self.metrics = SimulationMetrics()
        self.robot_task_stage.clear()
        self.coordinator.consecutive_waits.clear()
        for robot in self.robots.values():
            robot.reset_stats()
        for task in self.tasks.values():
            task.status = TaskStatus.PENDING
            task.assigned_robot_id = None
            task.completed_at_tick = None
