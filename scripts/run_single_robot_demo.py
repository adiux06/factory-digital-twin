"""
FactoryTwin - Single Robot CLI Demonstration
Demonstrates a mobile robot navigating an industrial facility avoiding storage shelves.
"""

import sys
import os
import time

# Ensure backend is on python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from app.simulation.grid import GridMap, Position, CellType
from app.simulation.robot import RobotState
from app.simulation.engine import SimulationEngine


def render_ascii_grid(engine: SimulationEngine) -> str:
    grid = engine.grid
    chars = []
    robot_positions = {r.position: r.id for r in engine.robots.values()}
    
    header = f"--- FactoryTwin Tick {engine.tick:03d} | Robot: {list(engine.robots.keys())[0]} ---"
    chars.append(header)
    
    for y in range(grid.height):
        row = []
        for x in range(grid.width):
            pos = Position(x=x, y=y)
            if pos in robot_positions:
                row.append("🤖")
            elif pos in grid.static_obstacles:
                row.append("⬛")
            elif pos in grid.pickup_stations.values():
                row.append("📥")
            elif pos in grid.delivery_stations.values():
                row.append("📦")
            elif pos in grid.inspection_stations.values():
                row.append("🔬")
            elif pos in grid.charging_stations.values():
                row.append("⚡")
            else:
                row.append(" ·")
        chars.append("".join(row))
    return "\n".join(chars)


def main():
    print("=" * 60)
    print(" FactoryTwin - Autonomous Robot Navigation Demo")
    print("=" * 60)
    
    grid = GridMap.create_default_factory()
    engine = SimulationEngine(grid=grid)
    
    # Start at charging pad DOCK_1 (4, 13)
    start_pos = Position(x=4, y=13)
    # Destination: Assembly workstation 1 (9, 3)
    dest_pos = Position(x=9, y=3)
    
    robot = engine.add_robot("AGV-ALPHA", start_pos)
    print(f"Robot {robot.id} spawned at {start_pos.to_tuple()}")
    print(f"Goal: Workstation at {dest_pos.to_tuple()}")
    
    success = engine.plan_route_for_robot(robot.id, dest_pos)
    if not success:
        print("ERROR: Failed to plan route!")
        return
        
    print(f"Path planned! Waypoints ({len(robot.planned_path)} steps):")
    print(" -> ".join([str(p.to_tuple()) for p in robot.planned_path[:6]]) + " ... " + str(dest_pos.to_tuple()))
    print("\nSimulating navigation ticks:")
    
    max_ticks = 40
    while robot.status == RobotState.MOVING and engine.tick < max_ticks:
        engine.step()
        print(f"Tick {engine.tick:02d}: Robot at {robot.position.to_tuple()} (Status: {robot.status.value})")
        
    print("-" * 60)
    print(f"Simulation completed at Tick {engine.tick}")
    print(f"Final Robot Status: {robot.status.value}")
    print(f"Total Distance Travelled: {robot.distance_travelled} cells")
    print(f"Final Position: {robot.position.to_tuple()}")
    assert robot.position == dest_pos, "Robot should have reached the target destination!"
    print("SUCCESS: Target destination reached safely without traversing shelves or obstacles.")


if __name__ == "__main__":
    main()
