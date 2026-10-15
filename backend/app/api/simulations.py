import uuid
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session

from app.schemas.simulation import (
    CreateSimulationRequest,
    CreateTaskRequest,
    AddObstacleRequest,
    TriggerFaultRequest,
    RecoverRobotRequest,
    SpeedControlRequest,
    ScenarioResponse,
)
from app.simulation.grid import Position
from app.simulation.task import Task
from app.services.simulation_manager import simulation_manager
from app.db.session import get_db
from app.db.models import SimulationRunRecord, TaskRecord

router = APIRouter(prefix="/simulations", tags=["Simulations"])


@router.get("/scenarios", response_model=List[ScenarioResponse])
def get_scenarios():
    return [
        ScenarioResponse(
            id="default_factory",
            name="Advanced Automotive Assembly & Inspection Facility",
            description="20x15 industrial layout with storage racks, dual assembly cells, automated QC inspection bay, and AGV charging docks.",
            width=20,
            height=15,
            stations_count=13,
        ),
        ScenarioResponse(
            id="congested_warehouse",
            name="Congested High-Density Aisle Warehouse",
            description="High-density logistics setting with narrow corridors designed for stress-testing collision avoidance and multi-agent coordination.",
            width=20,
            height=15,
            stations_count=8,
        ),
    ]


@router.post("")
def create_simulation(req: CreateSimulationRequest):
    sim = simulation_manager.create_simulation(
        scheduling_policy=req.scheduling_policy,
        num_robots=req.num_robots,
        scenario_id=req.scenario_id or "default_factory",
    )
    return {
        "simulation_id": sim.id,
        "scheduling_policy": req.scheduling_policy.value,
        "robots_count": len(sim.engine.robots),
        "state": sim.engine.get_state(),
    }


@router.get("/{sim_id}")
def get_simulation_state(sim_id: str):
    sim = None
    if sim_id and sim_id != "default":
        sim = simulation_manager.get_simulation(sim_id)
    if not sim and simulation_manager.simulations:
        sim = next(iter(simulation_manager.simulations.values()))
    if not sim:
        raise HTTPException(status_code=404, detail=f"Simulation {sim_id} not found")
    return sim.engine.get_state()


@router.post("/{sim_id}/start")
def start_simulation(sim_id: str):
    sim = simulation_manager.get_simulation(sim_id)
    if not sim:
        raise HTTPException(status_code=404, detail="Simulation not found")
    success = simulation_manager.start_simulation(sim_id)
    return {"status": "started" if success else "already_running"}


@router.post("/{sim_id}/pause")
def pause_simulation(sim_id: str):
    sim = simulation_manager.get_simulation(sim_id)
    if not sim:
        raise HTTPException(status_code=404, detail="Simulation not found")
    success = simulation_manager.pause_simulation(sim_id)
    return {"status": "paused" if success else "already_paused"}


@router.post("/{sim_id}/resume")
def resume_simulation(sim_id: str):
    sim = simulation_manager.get_simulation(sim_id)
    if not sim:
        raise HTTPException(status_code=404, detail="Simulation not found")
    success = simulation_manager.start_simulation(sim_id)
    return {"status": "resumed" if success else "already_running"}


@router.post("/{sim_id}/step")
def step_simulation(sim_id: str):
    sim = simulation_manager.get_simulation(sim_id)
    if not sim:
        raise HTTPException(status_code=404, detail="Simulation not found")
    simulation_manager.step_simulation(sim_id)
    return sim.engine.get_state()


@router.post("/{sim_id}/reset")
def reset_simulation(sim_id: str):
    sim = simulation_manager.get_simulation(sim_id)
    if not sim:
        raise HTTPException(status_code=404, detail="Simulation not found")
    simulation_manager.reset_simulation(sim_id)
    return sim.engine.get_state()


@router.post("/{sim_id}/speed")
def adjust_speed(sim_id: str, req: SpeedControlRequest):
    sim = simulation_manager.get_simulation(sim_id)
    if not sim:
        raise HTTPException(status_code=404, detail="Simulation not found")
    sim.speed_multiplier = req.speed_multiplier
    return {"speed_multiplier": sim.speed_multiplier}


@router.post("/{sim_id}/tasks")
def create_task(sim_id: str, req: CreateTaskRequest, db: Session = Depends(get_db)):
    sim = simulation_manager.get_simulation(sim_id)
    if not sim:
        raise HTTPException(status_code=404, detail="Simulation not found")

    task_id = f"TASK-{uuid.uuid4().hex[:6].upper()}"
    task = Task(
        id=task_id,
        pickup_location=Position(x=req.pickup_x, y=req.pickup_y),
        destination=Position(x=req.dest_x, y=req.dest_y),
        priority=req.priority,
        requires_inspection=req.requires_inspection,
        item_type=req.item_type,
        created_at_tick=sim.engine.tick,
    )
    sim.engine.add_task(task)

    # Persist task record
    try:
        rec = TaskRecord(
            id=task_id,
            run_id=sim_id,
            item_type=req.item_type,
            priority=req.priority.value,
            pickup_x=req.pickup_x,
            pickup_y=req.pickup_y,
            dest_x=req.dest_x,
            dest_y=req.dest_y,
            created_at_tick=sim.engine.tick,
        )
        db.add(rec)
        db.commit()
    except Exception:
        pass

    return {"task_id": task_id, "status": "QUEUED"}


@router.post("/{sim_id}/obstacles")
def add_obstacle(sim_id: str, req: AddObstacleRequest):
    sim = simulation_manager.get_simulation(sim_id)
    if not sim:
        raise HTTPException(status_code=404, detail="Simulation not found")

    obs_id = f"OBS-{uuid.uuid4().hex[:6].upper()}"
    success = sim.engine.add_dynamic_obstacle(
        obstacle_id=obs_id,
        pos=Position(x=req.x, y=req.y),
        duration=req.duration_ticks,
    )
    if not success:
        raise HTTPException(status_code=400, detail="Invalid obstacle position or cell already blocked")

    return {"obstacle_id": obs_id, "x": req.x, "y": req.y}


@router.delete("/{sim_id}/obstacles/{obstacle_id}")
def remove_obstacle(sim_id: str, obstacle_id: str):
    sim = simulation_manager.get_simulation(sim_id)
    if not sim:
        raise HTTPException(status_code=404, detail="Simulation not found")

    success = sim.engine.remove_dynamic_obstacle(obstacle_id)
    if not success:
        raise HTTPException(status_code=404, detail="Obstacle not found")

    return {"status": "removed", "obstacle_id": obstacle_id}


@router.post("/{sim_id}/faults")
def trigger_fault(sim_id: str, req: TriggerFaultRequest):
    sim = simulation_manager.get_simulation(sim_id)
    if not sim:
        raise HTTPException(status_code=404, detail="Simulation not found")

    success = sim.engine.trigger_robot_fault(req.robot_id, req.reason)
    if not success:
        raise HTTPException(status_code=404, detail="Robot not found")

    return {"status": "faulted", "robot_id": req.robot_id}


@router.post("/{sim_id}/recover")
def recover_robot(sim_id: str, req: RecoverRobotRequest):
    sim = simulation_manager.get_simulation(sim_id)
    if not sim:
        raise HTTPException(status_code=404, detail="Simulation not found")

    success = sim.engine.recover_robot(req.robot_id)
    if not success:
        raise HTTPException(status_code=400, detail="Robot not found or not in FAULTED state")

    return {"status": "recovered", "robot_id": req.robot_id}


@router.get("/{sim_id}/metrics")
def get_metrics(sim_id: str):
    sim = simulation_manager.get_simulation(sim_id)
    if not sim:
        raise HTTPException(status_code=404, detail="Simulation not found")
    return sim.engine.metrics.model_dump()
