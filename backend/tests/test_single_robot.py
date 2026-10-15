import pytest
from app.simulation.grid import CellType, GridMap, Position
from app.simulation.robot import Robot, RobotState
from app.simulation.engine import SimulationEngine


def test_robot_reaches_destination():
    grid = GridMap(width=10, height=10)
    engine = SimulationEngine(grid=grid)
    
    start = Position(x=1, y=1)
    goal = Position(x=1, y=4)
    
    robot = engine.add_robot("AGV-01", start)
    assert robot.status == RobotState.IDLE
    
    # Plan path
    success = engine.plan_route_for_robot("AGV-01", goal)
    assert success is True
    assert robot.status == RobotState.MOVING
    assert len(robot.planned_path) == 4  # (1,1)->(1,2)->(1,3)->(1,4)
    
    # Step engine until completion
    step_count = 0
    while robot.status == RobotState.MOVING and step_count < 10:
        engine.step()
        step_count += 1
        
    assert robot.position == goal
    assert robot.status == RobotState.COMPLETED
    assert robot.distance_travelled == 3
    assert engine.metrics.total_distance_travelled == 3


def test_robot_cannot_move_through_wall():
    grid = GridMap(width=10, height=10)
    # Put a wall at (1, 2)
    grid.set_cell_type(Position(x=1, y=2), CellType.WALL)
    
    engine = SimulationEngine(grid=grid)
    start = Position(x=1, y=1)
    goal = Position(x=1, y=3)
    
    robot = engine.add_robot("AGV-01", start)
    # Plan path - A* must route around the wall
    success = engine.plan_route_for_robot("AGV-01", goal)
    assert success is True
    
    # Ensure (1,2) is never stepped on
    while robot.status == RobotState.MOVING:
        engine.step()
        assert robot.position != Position(x=1, y=2), "Robot illegally traversed wall!"
        
    assert robot.position == goal
    assert robot.status == RobotState.COMPLETED


def test_unreachable_destination_handled():
    grid = GridMap(width=6, height=6)
    # Enclose (4,4)
    for p in [Position(x=3, y=4), Position(x=5, y=4), Position(x=4, y=3), Position(x=4, y=5)]:
        grid.set_cell_type(p, CellType.WALL)
        
    engine = SimulationEngine(grid=grid)
    robot = engine.add_robot("AGV-01", Position(x=1, y=1))
    
    success = engine.plan_route_for_robot("AGV-01", Position(x=4, y=4))
    assert success is False
    assert robot.status == RobotState.IDLE
    assert robot.planned_path == []


def test_reset_restores_state():
    grid = GridMap(width=5, height=5)
    engine = SimulationEngine(grid=grid)
    robot = engine.add_robot("AGV-01", Position(x=0, y=0))
    engine.plan_route_for_robot("AGV-01", Position(x=0, y=3))
    
    engine.step()
    engine.step()
    assert engine.tick == 2
    assert robot.distance_travelled == 2
    
    engine.reset()
    assert engine.tick == 0
    assert robot.distance_travelled == 0
    assert robot.status == RobotState.IDLE
