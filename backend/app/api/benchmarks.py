import uuid
from typing import Dict, List, Optional
from fastapi import APIRouter, Query, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.simulation.grid import GridMap, Position
from app.simulation.engine import SimulationEngine
from app.simulation.scheduler import SchedulingPolicy
from app.simulation.task import Task, TaskPriority
from app.db.session import get_db
from app.db.models import BenchmarkRecord

router = APIRouter(prefix="/benchmarks", tags=["Benchmarks"])


class BenchmarkRunRequest(BaseModel):
    num_robots: int = 3
    num_tasks: int = 6
    max_ticks: int = 120
    seed: int = 42


def run_benchmark_trial(
    policy: SchedulingPolicy,
    scenario_name: str,
    num_robots: int = 3,
    num_tasks: int = 6,
    max_ticks: int = 120,
    seed: int = 42,
) -> dict:
    """Executes a headless deterministic simulation trial and collects performance metrics."""
    grid = GridMap.create_default_factory()
    engine = SimulationEngine(grid=grid, random_seed=seed, scheduling_policy=policy)

    dock_positions = [
        Position(x=4, y=13),
        Position(x=6, y=13),
        Position(x=14, y=13),
        Position(x=16, y=13),
    ]
    for i in range(min(num_robots, len(dock_positions))):
        engine.add_robot(f"AGV-{i+1:02d}", dock_positions[i])

    # Deterministic task generation using seed
    import random
    rng = random.Random(seed)
    pickups = [Position(x=1, y=2), Position(x=1, y=6), Position(x=1, y=10)]
    deliveries = [Position(x=18, y=2), Position(x=18, y=6), Position(x=18, y=10), Position(x=10, y=12)]

    for t_idx in range(num_tasks):
        p = rng.choice(pickups)
        d = rng.choice(deliveries)
        task = Task(
            id=f"BM-T{t_idx+1:02d}",
            pickup_location=p,
            destination=d,
            priority=TaskPriority.HIGH if t_idx % 2 == 0 else TaskPriority.MEDIUM,
            created_at_tick=0,
        )
        engine.add_task(task)

    # Run discrete ticks until max_ticks or all tasks completed
    while engine.tick < max_ticks and engine.metrics.tasks_completed < num_tasks:
        engine.step()

    delivery_times = [
        t.completed_at_tick - t.created_at_tick
        for t in engine.tasks.values()
        if t.completed_at_tick is not None
    ]
    avg_delivery = float(sum(delivery_times) / len(delivery_times)) if delivery_times else 0.0

    return {
        "scenario": scenario_name,
        "policy": policy.value,
        "num_robots": num_robots,
        "num_tasks": num_tasks,
        "ticks_executed": engine.tick,
        "tasks_completed": engine.metrics.tasks_completed,
        "tasks_failed": engine.metrics.tasks_failed,
        "completion_rate_pct": round((engine.metrics.tasks_completed / num_tasks) * 100.0, 1),
        "total_distance": engine.metrics.total_distance_travelled,
        "total_waiting_time": engine.metrics.total_wait_ticks,
        "throughput_per_100_ticks": round(engine.metrics.throughput_per_100_ticks, 2),
        "avg_delivery_time": round(avg_delivery, 1),
        "replans_count": engine.metrics.replans_count,
        "conflicts_prevented": engine.metrics.conflicts_prevented,
        "actual_collisions": engine.metrics.actual_collisions,
    }


@router.post("/run")
def execute_benchmark(req: BenchmarkRunRequest, db: Session = Depends(get_db)):
    results = []
    policies = [SchedulingPolicy.FIFO, SchedulingPolicy.NEAREST_ROBOT]

    for pol in policies:
        res = run_benchmark_trial(
            policy=pol,
            scenario_name="Automotive Manufacturing Floor",
            num_robots=req.num_robots,
            num_tasks=req.num_tasks,
            max_ticks=req.max_ticks,
            seed=req.seed,
        )
        results.append(res)

        # Persist to database
        try:
            rec = BenchmarkRecord(
                id=f"BM-{uuid.uuid4().hex[:8].upper()}",
                scenario_category=res["scenario"],
                scheduling_policy=res["policy"],
                num_robots=res["num_robots"],
                num_tasks=res["num_tasks"],
                total_ticks=res["ticks_executed"],
                tasks_completed=res["tasks_completed"],
                tasks_failed=res["tasks_failed"],
                throughput=res["throughput_per_100_ticks"],
                avg_delivery_time=res["avg_delivery_time"],
                total_distance=res["total_distance"],
                replans_count=res["replans_count"],
                conflicts_prevented=res["conflicts_prevented"],
                actual_collisions=res["actual_collisions"],
                seed=req.seed,
            )
            db.add(rec)
            db.commit()
        except Exception:
            pass

    return {
        "trials": results,
        "comparison": {
            "fifo_completion": results[0]["completion_rate_pct"],
            "nearest_completion": results[1]["completion_rate_pct"],
            "fifo_avg_delivery": results[0]["avg_delivery_time"],
            "nearest_avg_delivery": results[1]["avg_delivery_time"],
            "fifo_distance": results[0]["total_distance"],
            "nearest_distance": results[1]["total_distance"],
        },
    }


@router.get("")
def get_benchmarks_history(limit: int = Query(20, ge=1, le=100), db: Session = Depends(get_db)):
    records = db.query(BenchmarkRecord).order_by(BenchmarkRecord.created_at.desc()).limit(limit).all()
    return [
        {
            "id": r.id,
            "scenario": r.scenario_category,
            "policy": r.scheduling_policy,
            "num_robots": r.num_robots,
            "num_tasks": r.num_tasks,
            "throughput": r.throughput,
            "avg_delivery_time": r.avg_delivery_time,
            "total_distance": r.total_distance,
            "replans_count": r.replans_count,
            "conflicts_prevented": r.conflicts_prevented,
            "actual_collisions": r.actual_collisions,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in records
    ]
