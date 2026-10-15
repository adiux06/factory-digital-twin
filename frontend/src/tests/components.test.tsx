import { describe, it, expect } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { RobotStatusCards } from '../features/robots/RobotStatusCards';
import { TaskManagementPanel } from '../features/tasks/TaskManagementPanel';
import { EventFeed } from '../features/simulation/EventFeed';
import { FactoryMapCanvas } from '../features/simulation/FactoryMapCanvas';
import type { Robot, Task, GridMapData, SimulationEvent } from '../types';

describe('FactoryTwin Frontend Components', () => {
  it('renders RobotStatusCards with active AGV telemetry', () => {
    const mockRobots: Record<string, Robot> = {
      'AGV-01': {
        id: 'AGV-01',
        position: { x: 4, y: 13 },
        destination: { x: 9, y: 3 },
        task_id: 'TASK-101',
        status: 'MOVING',
        planned_path: [],
        path_index: 0,
        distance_travelled: 12,
        tasks_completed: 2,
        total_waiting_time: 0,
        current_fault: null,
        battery_level: 95.0,
      },
    };

    render(
      <RobotStatusCards
        robots={mockRobots}
        selectedRobotId={null}
        onSelectRobot={() => {}}
        onTriggerFault={() => {}}
        onRecoverRobot={() => {}}
      />
    );

    expect(screen.getByText('AGV Fleet Telemetry')).toBeDefined();
    expect(screen.getByText('AGV-01')).toBeDefined();
    expect(screen.getByText('MOVING')).toBeDefined();
    expect(screen.getByText('12m')).toBeDefined();
  });

  it('renders TaskManagementPanel and toggles create drawer', () => {
    const mockTasks: Record<string, Task> = {
      'TASK-01': {
        id: 'TASK-01',
        pickup_location: { x: 1, y: 2 },
        destination: { x: 9, y: 3 },
        priority: 'HIGH',
        created_at_tick: 1,
        status: 'PENDING',
        assigned_robot_id: null,
        completed_at_tick: null,
        failure_reason: null,
        requires_inspection: false,
        inspection_image_id: null,
        item_type: 'Machined Flange',
      },
    };

    render(<TaskManagementPanel tasks={mockTasks} onCreateTask={() => {}} />);

    expect(screen.getByText('Production Tasks')).toBeDefined();
    expect(screen.getByText('TASK-01')).toBeDefined();
    expect(screen.getByText('Machined Flange')).toBeDefined();

    // Click "New Task"
    const newBtn = screen.getByText('New Task');
    fireEvent.click(newBtn);
    expect(screen.getByText('Create Factory Work Order')).toBeDefined();
  });

  it('renders EventFeed with filterable telemetry logs', () => {
    const mockEvents: SimulationEvent[] = [
      {
        tick: 10,
        event_type: 'robot.path_planned',
        message: 'Path planned for AGV-01: cost 15',
        data: {},
      },
      {
        tick: 12,
        event_type: 'conflict.prevented',
        message: 'Coordinator prevented vertex conflict',
        data: {},
      },
    ];

    render(<EventFeed events={mockEvents} />);

    expect(screen.getByText('Live Simulation Telemetry Stream')).toBeDefined();
    expect(screen.getByText('Path planned for AGV-01: cost 15')).toBeDefined();
    expect(screen.getByText('Coordinator prevented vertex conflict')).toBeDefined();
  });

  it('renders FactoryMapCanvas without throwing errors', () => {
    const mockGrid: GridMapData = {
      width: 5,
      height: 5,
      static_obstacles: [{ x: 2, y: 2 }],
      cell_types: {},
      workstations: {},
      pickup_stations: { P1: { x: 1, y: 1 } },
      delivery_stations: { D1: { x: 4, y: 4 } },
      inspection_stations: {},
      charging_stations: {},
      dynamic_obstacles: [],
    };

    const { container } = render(
      <FactoryMapCanvas
        grid={mockGrid}
        robots={{}}
        tasks={{}}
        selectedRobotId={null}
        onSelectRobot={() => {}}
        onCellClick={() => {}}
      />
    );

    expect(container.querySelector('svg')).toBeDefined();
  });
});
