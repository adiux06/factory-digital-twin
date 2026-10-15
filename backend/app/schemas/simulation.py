from typing import Dict, List, Optional
from pydantic import BaseModel, Field
from app.simulation.scheduler import SchedulingPolicy
from app.simulation.task import TaskPriority


class CreateSimulationRequest(BaseModel):
    scenario_id: Optional[str] = "default_factory"
    scheduling_policy: SchedulingPolicy = SchedulingPolicy.NEAREST_ROBOT
    num_robots: int = Field(default=3, ge=1, le=8)


class CreateTaskRequest(BaseModel):
    pickup_x: int
    pickup_y: int
    dest_x: int
    dest_y: int
    priority: TaskPriority = TaskPriority.MEDIUM
    requires_inspection: bool = False
    item_type: str = "Standard Part"


class AddObstacleRequest(BaseModel):
    x: int
    y: int
    duration_ticks: Optional[int] = None


class TriggerFaultRequest(BaseModel):
    robot_id: str
    reason: str = "Motor drive stall"


class RecoverRobotRequest(BaseModel):
    robot_id: str


class SpeedControlRequest(BaseModel):
    speed_multiplier: float = Field(default=1.0, ge=0.25, le=5.0)


class ScenarioResponse(BaseModel):
    id: str
    name: str
    description: str
    width: int
    height: int
    stations_count: int
