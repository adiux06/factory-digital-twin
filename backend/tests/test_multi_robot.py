import pytest
from app.simulation.grid import CellType, GridMap, Position
from app.simulation.robot import Robot, RobotState
from app.simulation.task import Task, TaskStatus, TaskPriority
from app.simulation.engine import SimulationEngine


def test_simultaneous_robot_movement():
    grid = GridMap(width=10, height=10)
    engine = SimulationEngine(grid=grid)

    # Robot 1 moves horizontally on row 1
    # Robot 2 moves horizontally on row 3
    r1 = engine.add_robot("AGV-1", Position(x=0, y=1))
    r2 = engine.add_robot("AGV-2", Position(x=0, y=3))

    dest1 = Position(x=5, y=1)
    dest2 = Position(x=5, y=3)

    engine.plan_route_for_robot("AGV-1", dest1)
    engine.plan_route_for_robot("AGV-2", dest2)

    # Step until both reach destination
    for _ in range(10):
        engine.step()

    assert r1.position == dest1
    assert r2.position == dest2
    assert r1.status == RobotState.COMPLETED
    assert r2.status == RobotState.COMPLETED
    assert engine.metrics.actual_collisions == 0


def test_head_on_edge_swap_prevented():
    """
    Two robots facing each other in a narrow corridor:
    Robot 1 at (2, 2) wanting to move to (3, 2).
    Robot 2 at (3, 2) wanting to move to (2, 2).
    The coordinator must reject the simultaneous swap.
    """
    grid = GridMap(width=10, height=10)
    # Surround row 2 with walls above and below
    for x in range(1, 5):
        grid.set_cell_type(Position(x=x, y=1), CellType.WALL)
        grid.set_cell_type(Position(x=x, y=3), CellType.WALL)

    engine = SimulationEngine(grid=grid)
    r1 = engine.add_robot("AGV-1", Position(x=2, y=2))
    r2 = engine.add_robot("AGV-2", Position(x=3, y=2))

    # Give paths that swap directly
    r1.assign_path([Position(x=2, y=2), Position(x=3, y=2)], Position(x=3, y=2))
    r2.assign_path([Position(x=3, y=2), Position(x=2, y=2)], Position(x=2, y=2))

    # Single step
    engine.step()

    # Neither should have swapped illegally into each other's cell in one step
    assert r1.position != Position(x=3, y=2) or r2.position != Position(x=2, y=2)
    assert engine.metrics.conflicts_prevented >= 1
    assert engine.metrics.actual_collisions == 0


def test_vertex_conflict_prevented():
    """
    Robot 1 at (2, 1) and Robot 2 at (4, 1), both moving towards (3, 1) at the same tick.
    Only one should enter (3, 1); the other must yield.
    """
    grid = GridMap(width=10, height=10)
    engine = SimulationEngine(grid=grid)

    r1 = engine.add_robot("AGV-A", Position(x=2, y=1))
    r2 = engine.add_robot("AGV-B", Position(x=4, y=1))

    target = Position(x=3, y=1)
    r1.assign_path([Position(x=2, y=1), target], target)
    r2.assign_path([Position(x=4, y=1), target], target)

    engine.step()

    # Check positions: exactly one robot is at target, the other stayed or yielded
    positions = [r1.position, r2.position]
    assert target in positions
    assert len(set(positions)) == 2  # distinct positions
    assert engine.metrics.conflicts_prevented >= 1
    assert engine.metrics.actual_collisions == 0


def test_task_lifecycle_execution():
    """
    Full task workflow: robot assigned -> navigates to pickup -> picks up -> delivers -> completes.
    """
    grid = GridMap.create_default_factory()
    engine = SimulationEngine(grid=grid)

    robot = engine.add_robot("AGV-01", Position(x=4, y=13))  # Dock 1
    pickup = Position(x=1, y=2)   # Pickup A
    dest = Position(x=9, y=3)     # Assembly 1

    task = Task(id="TASK-101", pickup_location=pickup, destination=dest)
    engine.add_task(task)

    success = engine.assign_task_to_robot(task.id, robot.id)
    assert success is True
    assert task.status == TaskStatus.ASSIGNED

    # Advance simulation
    max_steps = 50
    steps = 0
    while task.status != TaskStatus.COMPLETED and steps < max_steps:
        engine.step()
        steps += 1

    assert task.status == TaskStatus.COMPLETED
    assert robot.tasks_completed == 1
    assert engine.metrics.tasks_completed == 1
    assert robot.position == dest
    assert engine.metrics.actual_collisions == 0


def test_dynamic_obstacle_and_replanning():
    """
    Placing a dynamic obstacle on a robot's planned path triggers route invalidation & replanning.
    """
    grid = GridMap(width=10, height=10)
    engine = SimulationEngine(grid=grid)

    robot = engine.add_robot("AGV-01", Position(x=1, y=1))
    goal = Position(x=1, y=5)
    engine.plan_route_for_robot("AGV-01", goal)

    # Initial path: (1,1) -> (1,2) -> (1,3) -> (1,4) -> (1,5)
    assert Position(x=1, y=3) in robot.planned_path

    # Step once
    engine.step()
    assert robot.position == Position(x=1, y=2)

    # Place dynamic obstacle at (1, 3)
    engine.add_dynamic_obstacle("BARRIER-1", Position(x=1, y=3))

    # Stepping forward should route around the obstacle
    max_steps = 20
    steps = 0
    while robot.position != goal and steps < max_steps:
        engine.step()
        steps += 1

    assert robot.position == goal
    assert engine.metrics.replans_count >= 1
    assert engine.metrics.actual_collisions == 0


def test_simulated_robot_fault_and_task_preservation():
    """
    When a robot faults, it does not silently lose its assigned task.
    """
    grid = GridMap(width=10, height=10)
    engine = SimulationEngine(grid=grid)

    r1 = engine.add_robot("AGV-01", Position(x=1, y=1))
    task = Task(id="TASK-FAULT-TEST", pickup_location=Position(x=1, y=2), destination=Position(x=5, y=5))
    engine.add_task(task)
    engine.assign_task_to_robot(task.id, r1.id)

    # Trigger fault
    engine.trigger_robot_fault(r1.id, "Emergency stop button pressed")

    assert r1.status == RobotState.FAULTED
    assert r1.current_fault == "Emergency stop button pressed"
    assert task.status == TaskStatus.FAILED
    assert "faulted" in task.failure_reason

    # Recover robot
    engine.recover_robot(r1.id)
    assert r1.status == RobotState.IDLE
    assert r1.current_fault is None
