from __future__ import annotations
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field

from app.simulation.grid import Position


class TaskPriority(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class TaskStatus(str, Enum):
    PENDING = "PENDING"
    ASSIGNED = "ASSIGNED"
    PICKING_UP = "PICKING_UP"
    DELIVERING = "DELIVERING"
    INSPECTION_PENDING = "INSPECTION_PENDING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class Task(BaseModel):
    id: str
    pickup_location: Position
    destination: Position
    priority: TaskPriority = TaskPriority.MEDIUM
    created_at_tick: int = 0
    status: TaskStatus = TaskStatus.PENDING
    assigned_robot_id: Optional[str] = None
    completed_at_tick: Optional[int] = None
    failure_reason: Optional[str] = None
    requires_inspection: bool = False
    inspection_image_id: Optional[str] = None
    item_type: str = "Standard Part"

    def mark_assigned(self, robot_id: str) -> None:
        self.assigned_robot_id = robot_id
        self.status = TaskStatus.ASSIGNED

    def mark_completed(self, tick: int) -> None:
        self.status = TaskStatus.COMPLETED
        self.completed_at_tick = tick

    def mark_failed(self, reason: str) -> None:
        self.status = TaskStatus.FAILED
        self.failure_reason = reason
        self.assigned_robot_id = None
