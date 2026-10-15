import React, { useState } from 'react';
import type { GridMapData, Robot, Position, Task } from '../../types';

interface FactoryMapProps {
  grid: GridMapData;
  robots: Record<string, Robot>;
  tasks: Record<string, Task>;
  selectedRobotId: string | null;
  onSelectRobot: (robotId: string | null) => void;
  onCellClick: (pos: Position) => void;
}

export const FactoryMapCanvas: React.FC<FactoryMapProps> = ({
  grid,
  robots,
  selectedRobotId,
  onSelectRobot,
  onCellClick,
}) => {
  const [hoveredCell, setHoveredCell] = useState<Position | null>(null);

  const cellSize = 38;
  const mapWidth = grid.width * cellSize;
  const mapHeight = grid.height * cellSize;

  // Static obstacle set for fast lookup
  const staticObstacleSet = new Set(
    grid.static_obstacles.map((p) => `${p.x},${p.y}`)
  );

  // Dynamic obstacle map
  const dynamicObstaclesMap = new Map<string, string>();
  grid.dynamic_obstacles.forEach((obs) => {
    dynamicObstaclesMap.set(`${obs.x},${obs.y}`, obs.id);
  });

  // Station lookups
  const isPickup = (x: number, y: number) =>
    Object.values(grid.pickup_stations).some((p) => p.x === x && p.y === y);
  const isDelivery = (x: number, y: number) =>
    Object.values(grid.delivery_stations).some((p) => p.x === x && p.y === y);
  const isInspection = (x: number, y: number) =>
    Object.values(grid.inspection_stations).some((p) => p.x === x && p.y === y);
  const isWorkstation = (x: number, y: number) =>
    Object.values(grid.workstations).some((p) => p.x === x && p.y === y);
  const isCharging = (x: number, y: number) =>
    Object.values(grid.charging_stations).some((p) => p.x === x && p.y === y);

  // Status colors for robots
  const getRobotColor = (status: string) => {
    switch (status) {
      case 'MOVING':
        return '#06b6d4'; // Cyan
      case 'WAITING':
        return '#f59e0b'; // Amber
      case 'INSPECTING':
        return '#a855f7'; // Purple
      case 'FAULTED':
        return '#ef4444'; // Red
      case 'COMPLETED':
        return '#10b981'; // Emerald
      default:
        return '#64748b'; // Slate
    }
  };

  return (
    <div className="relative bg-[#0c1322] border border-slate-800 rounded-xl p-3 shadow-2xl overflow-auto select-none">
      {/* Top Map Header & Legend */}
      <div className="flex flex-wrap items-center justify-between pb-3 mb-2 border-b border-slate-800/80 text-xs text-slate-400 gap-2">
        <div className="flex items-center space-x-2">
          <span className="font-mono font-medium text-cyan-400 uppercase tracking-wider">
            Factory Floor Digital Twin
          </span>
          <span className="text-slate-600">|</span>
          <span>
            Grid: {grid.width} &times; {grid.height} ({grid.width * grid.height} cells)
          </span>
          {hoveredCell && (
            <span className="bg-slate-800 text-slate-200 px-2 py-0.5 rounded font-mono">
              X:{hoveredCell.x} Y:{hoveredCell.y}
            </span>
          )}
        </div>

        {/* Legend pills */}
        <div className="flex flex-wrap items-center gap-3">
          <div className="flex items-center space-x-1.5">
            <span className="w-3 h-3 rounded-sm bg-slate-800 border border-slate-600 inline-block"></span>
            <span>Shelving Rack</span>
          </div>
          <div className="flex items-center space-x-1.5">
            <span className="w-3 h-3 rounded-sm bg-amber-500/20 border border-amber-500 inline-block"></span>
            <span>Pickup Bay</span>
          </div>
          <div className="flex items-center space-x-1.5">
            <span className="w-3 h-3 rounded-sm bg-emerald-500/20 border border-emerald-500 inline-block"></span>
            <span>Delivery Bay</span>
          </div>
          <div className="flex items-center space-x-1.5">
            <span className="w-3 h-3 rounded-sm bg-purple-500/20 border border-purple-500 inline-block"></span>
            <span>QC Vision Bay</span>
          </div>
          <div className="flex items-center space-x-1.5">
            <span className="w-3 h-3 rounded-sm bg-rose-500/30 border border-rose-500 inline-block"></span>
            <span>Blockage</span>
          </div>
        </div>
      </div>

      {/* SVG Canvas Map */}
      <div className="flex justify-center">
        <svg
          width={mapWidth}
          height={mapHeight}
          className="rounded-lg shadow-inner bg-[#070b14]"
        >
          {/* Subtle Grid Lines & Background Cells */}
          {Array.from({ length: grid.height }).map((_, y) =>
            Array.from({ length: grid.width }).map((_, x) => {
              const key = `${x},${y}`;
              const isWall = staticObstacleSet.has(key);
              const isDynamic = dynamicObstaclesMap.has(key);
              const pickup = isPickup(x, y);
              const delivery = isDelivery(x, y);
              const inspection = isInspection(x, y);
              const workstation = isWorkstation(x, y);
              const charging = isCharging(x, y);

              let fillColor = '#070b14';
              let strokeColor = '#162238';

              if (isWall) {
                fillColor = '#151e33';
                strokeColor = '#1e2d4d';
              } else if (isDynamic) {
                fillColor = '#881337'; // Rose hazard
                strokeColor = '#f43f5e';
              } else if (inspection) {
                fillColor = '#3b0764'; // Deep purple
                strokeColor = '#a855f7';
              } else if (pickup) {
                fillColor = '#451a03'; // Amber
                strokeColor = '#f59e0b';
              } else if (delivery) {
                fillColor = '#064e3b'; // Emerald
                strokeColor = '#10b981';
              } else if (workstation) {
                fillColor = '#172554'; // Blue
                strokeColor = '#3b82f6';
              } else if (charging) {
                fillColor = '#1c1917';
                strokeColor = '#eab308';
              }

              return (
                <g key={key}>
                  <rect
                    x={x * cellSize}
                    y={y * cellSize}
                    width={cellSize}
                    height={cellSize}
                    fill={fillColor}
                    stroke={strokeColor}
                    strokeWidth={0.7}
                    className="cursor-pointer transition-colors duration-150 hover:opacity-85"
                    onClick={() => onCellClick({ x, y })}
                    onMouseEnter={() => setHoveredCell({ x, y })}
                    onMouseLeave={() => setHoveredCell(null)}
                  />

                  {/* Icon overlays for stations */}
                  {isWall && (
                    <line
                      x1={x * cellSize + 4}
                      y1={y * cellSize + 4}
                      x2={(x + 1) * cellSize - 4}
                      y2={(y + 1) * cellSize - 4}
                      stroke="#27395e"
                      strokeWidth={1.5}
                    />
                  )}

                  {isDynamic && (
                    <text
                      x={x * cellSize + cellSize / 2}
                      y={y * cellSize + cellSize / 2 + 4}
                      textAnchor="middle"
                      fill="#f43f5e"
                      fontSize="14"
                      fontWeight="bold"
                    >
                      &times;
                    </text>
                  )}

                  {inspection && (
                    <text
                      x={x * cellSize + cellSize / 2}
                      y={y * cellSize + cellSize / 2 + 3}
                      textAnchor="middle"
                      fill="#c084fc"
                      fontSize="10"
                      fontWeight="bold"
                    >
                      QC
                    </text>
                  )}

                  {pickup && (
                    <text
                      x={x * cellSize + cellSize / 2}
                      y={y * cellSize + cellSize / 2 + 3}
                      textAnchor="middle"
                      fill="#fbbf24"
                      fontSize="10"
                      fontWeight="bold"
                    >
                      IN
                    </text>
                  )}

                  {delivery && (
                    <text
                      x={x * cellSize + cellSize / 2}
                      y={y * cellSize + cellSize / 2 + 3}
                      textAnchor="middle"
                      fill="#34d399"
                      fontSize="10"
                      fontWeight="bold"
                    >
                      OUT
                    </text>
                  )}

                  {charging && (
                    <text
                      x={x * cellSize + cellSize / 2}
                      y={y * cellSize + cellSize / 2 + 3}
                      textAnchor="middle"
                      fill="#facc15"
                      fontSize="11"
                    >
                      &zap;
                    </text>
                  )}
                </g>
              );
            })
          )}

          {/* Planned Paths of Robots */}
          {Object.values(robots).map((robot) => {
            if (!robot.planned_path || robot.planned_path.length < 2) return null;
            const points = robot.planned_path
              .slice(robot.path_index)
              .map(
                (p) =>
                  `${p.x * cellSize + cellSize / 2},${p.y * cellSize + cellSize / 2}`
              )
              .join(' ');

            const isSelected = selectedRobotId === robot.id;
            return (
              <polyline
                key={`path-${robot.id}`}
                points={points}
                fill="none"
                stroke={isSelected ? '#38bdf8' : '#0284c7'}
                strokeWidth={isSelected ? 2.8 : 1.6}
                strokeDasharray="4 3"
                opacity={isSelected ? 0.95 : 0.6}
              />
            );
          })}

          {/* Robots Render */}
          {Object.values(robots).map((robot) => {
            const rx = robot.position.x * cellSize + cellSize / 2;
            const ry = robot.position.y * cellSize + cellSize / 2;
            const color = getRobotColor(robot.status);
            const isSelected = selectedRobotId === robot.id;

            return (
              <g
                key={robot.id}
                className="cursor-pointer transition-transform duration-200"
                onClick={(e) => {
                  e.stopPropagation();
                  onSelectRobot(robot.id);
                }}
              >
                {isSelected && (
                  <circle
                    cx={rx}
                    cy={ry}
                    r={cellSize / 2 + 4}
                    fill="none"
                    stroke="#38bdf8"
                    strokeWidth={2}
                    className="animate-pulse"
                    opacity={0.8}
                  />
                )}

                <circle
                  cx={rx}
                  cy={ry}
                  r={cellSize / 2 - 3}
                  fill="#0f172a"
                  stroke={color}
                  strokeWidth={2.4}
                />

                <circle cx={rx} cy={ry} r={cellSize / 2 - 7} fill={color} opacity={0.25} />

                <text
                  x={rx}
                  y={ry + 3.5}
                  textAnchor="middle"
                  fill="#f8fafc"
                  fontSize="9"
                  fontFamily="monospace"
                  fontWeight="bold"
                >
                  {robot.id.replace('AGV-', '')}
                </text>
              </g>
            );
          })}
        </svg>
      </div>

      <div className="mt-2 text-center text-[11px] text-slate-500 font-sans">
        Click on any cell to place a dynamic barrier or assign tasks &bull; Click any robot to view real-time telemetry
      </div>
    </div>
  );
};
