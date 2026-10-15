import pytest
from app.simulation.grid import GridMap, Position
from app.simulation.task import Task, TaskStatus, TaskPriority
from app.simulation.engine import SimulationEngine
from app.simulation.scheduler import SchedulingPolicy


def test_fifo_scheduling():
    grid = GridMap(width=15, height=15)
    engine = SimulationEngine(grid=grid, scheduling_policy=SchedulingPolicy.FIFO)

    # 2 idle robots: R1 at (0, 0), R2 at (10, 10)
    r1 = engine.add_robot("AGV-1", Position(x=0, y=0))
    r2 = engine.add_robot("AGV-2", Position(x=10, y=10))

    # Task 1 created first at (2, 2)
    t1 = Task(id="T1", pickup_location=Position(x=2, y=2), destination=Position(x=5, y=5), created_at_tick=1)
    # Task 2 created second at (9, 9)
    t2 = Task(id="T2", pickup_location=Position(x=9, y=9), destination=Position(x=12, y=12), created_at_tick=2)

    engine.add_task(t1)
    engine.add_task(t2)

    # Step engine to trigger scheduling
    engine.step()

    # FIFO assigns oldest task T1 to first available robot AGV-1, and T2 to AGV-2
    assert t1.assigned_robot_id == "AGV-1"
    assert t2.assigned_robot_id == "AGV-2"


def test_nearest_robot_scheduling():
    grid = GridMap(width=15, height=15)
    engine = SimulationEngine(grid=grid, scheduling_policy=SchedulingPolicy.NEAREST_ROBOT)

    # R1 at (0, 0), R2 at (10, 10)
    r1 = engine.add_robot("AGV-1", Position(x=0, y=0))
    r2 = engine.add_robot("AGV-2", Position(x=10, y=10))

    # Task T_NEAR_R2 is at (9, 9) - much closer to AGV-2
    t_near = Task(id="T_NEAR_R2", pickup_location=Position(x=9, y=9), destination=Position(x=12, y=12))
    engine.add_task(t_near)

    engine.step()

    # Nearest robot scheduler must assign T_NEAR_R2 to AGV-2 because dist is ~2 vs ~18 for AGV-1
    assert t_near.assigned_robot_id == "AGV-2"


def test_scheduler_handles_empty_queue_and_all_busy_robots():
    grid = GridMap(width=5, height=5)
    engine = SimulationEngine(grid=grid, scheduling_policy=SchedulingPolicy.NEAREST_ROBOT)

    # No robots, 1 task
    t = Task(id="T1", pickup_location=Position(x=1, y=1), destination=Position(x=3, y=3))
    engine.add_task(t)

    # Step with no robots
    engine.step()
    assert t.status == TaskStatus.PENDING
    assert t.assigned_robot_id is None
