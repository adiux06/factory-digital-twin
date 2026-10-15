from __future__ import annotations
from enum import Enum
from typing import List, Optional, Set
from pydantic import BaseModel, Field

from app.simulation.grid import Position


class RobotState(str, Enum):
    IDLE = "IDLE"
    ASSIGNED = "ASSIGNED"
    MOVING = "MOVING"
    WAITING = "WAITING"
    INSPECTING = "INSPECTING"
    COMPLETED = "COMPLETED"
    FAULTED = "FAULTED"


# Explicit legal state transitions graph
LEGAL_TRANSITIONS: dict[RobotState, Set[RobotState]] = {
    RobotState.IDLE: {RobotState.ASSIGNED, RobotState.MOVING, RobotState.FAULTED},
    RobotState.ASSIGNED: {RobotState.MOVING, RobotState.WAITING, RobotState.FAULTED, RobotState.IDLE},
    RobotState.MOVING: {RobotState.MOVING, RobotState.WAITING, RobotState.INSPECTING, RobotState.COMPLETED, RobotState.IDLE, RobotState.FAULTED},
    RobotState.WAITING: {RobotState.MOVING, RobotState.WAITING, RobotState.FAULTED, RobotState.IDLE},
    RobotState.INSPECTING: {RobotState.MOVING, RobotState.COMPLETED, RobotState.IDLE, RobotState.FAULTED},
    RobotState.COMPLETED: {RobotState.IDLE, RobotState.ASSIGNED, RobotState.MOVING, RobotState.FAULTED},
    RobotState.FAULTED: {RobotState.IDLE, RobotState.WAITING},
}


class Robot(BaseModel):
    id: str
    position: Position
    destination: Optional[Position] = None
    task_id: Optional[str] = None
    status: RobotState = RobotState.IDLE
    planned_path: List[Position] = Field(default_factory=list)
    path_index: int = 0
    distance_travelled: int = 0
    tasks_completed: int = 0
    total_waiting_time: int = 0
    current_fault: Optional[str] = None
    battery_level: float = 100.0  # Optional realistic metric

    def can_transition_to(self, new_state: RobotState) -> bool:
        if self.status == new_state:
            return True
        allowed = LEGAL_TRANSITIONS.get(self.status, set())
        return new_state in allowed

    def set_state(self, new_state: RobotState, fault_reason: Optional[str] = None) -> bool:
        if not self.can_transition_to(new_state):
            raise ValueError(f"Illegal state transition from {self.status} to {new_state} for robot {self.id}")
        
        self.status = new_state
        if new_state == RobotState.FAULTED:
            self.current_fault = fault_reason or "Unknown hardware or navigation fault"
        elif new_state in (RobotState.IDLE, RobotState.COMPLETED):
            self.current_fault = None
            
        return True

    def assign_path(self, path: List[Position], destination: Position, task_id: Optional[str] = None) -> None:
        self.planned_path = path
        self.path_index = 0
        self.destination = destination
        if task_id:
            self.task_id = task_id
        if path and len(path) > 1:
            self.set_state(RobotState.MOVING)
        elif path and len(path) == 1:
            # Start == Goal
            self.set_state(RobotState.COMPLETED)

    def step_along_path(self) -> Optional[Position]:
        """
        Advances one step along the planned path.
        Returns the new position reached, or None if no movement occurred.
        """
        if self.status != RobotState.MOVING or not self.planned_path:
            return None

        # Check if we already reached destination
        if self.path_index + 1 >= len(self.planned_path):
            self.set_state(RobotState.COMPLETED)
            return self.position

        # Move to next node
        self.path_index += 1
        new_pos = self.planned_path[self.path_index]
        self.position = new_pos
        self.distance_travelled += 1
        self.battery_level = max(0.0, self.battery_level - 0.1)

        # Check if arrived at final waypoint
        if self.path_index >= len(self.planned_path) - 1:
            self.set_state(RobotState.COMPLETED)

        return self.position

    def record_wait_tick(self) -> None:
        self.total_waiting_time += 1
        if self.status != RobotState.FAULTED:
            self.set_state(RobotState.WAITING)

    def trigger_fault(self, reason: str = "Motor stalled or sensor occlusion") -> None:
        self.set_state(RobotState.FAULTED, fault_reason=reason)

    def recover_from_fault(self) -> None:
        if self.status == RobotState.FAULTED:
            self.set_state(RobotState.IDLE)
            self.current_fault = None
            self.planned_path = []
            self.path_index = 0
            self.destination = None

    def reset_stats(self) -> None:
        self.distance_travelled = 0
        self.tasks_completed = 0
        self.total_waiting_time = 0
        self.battery_level = 100.0
        self.current_fault = None
        self.planned_path = []
        self.path_index = 0
        self.destination = None
        self.task_id = None
        self.status = RobotState.IDLE
