import React from 'react';
import type { Robot } from '../../types';
import { Bot, Battery, Navigation } from 'lucide-react';

interface RobotStatusProps {
  robots: Record<string, Robot>;
  selectedRobotId: string | null;
  onSelectRobot: (robotId: string | null) => void;
  onTriggerFault: (robotId: string) => void;
  onRecoverRobot: (robotId: string) => void;
}

export const RobotStatusCards: React.FC<RobotStatusProps> = ({
  robots,
  selectedRobotId,
  onSelectRobot,
  onTriggerFault,
  onRecoverRobot,
}) => {
  const robotList = Object.values(robots);

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'MOVING':
        return <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-cyan-500/20 text-cyan-300 border border-cyan-500/40">MOVING</span>;
      case 'WAITING':
        return <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-amber-500/20 text-amber-300 border border-amber-500/40 animate-pulse">WAITING</span>;
      case 'INSPECTING':
        return <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-purple-500/20 text-purple-300 border border-purple-500/40 animate-pulse">INSPECTING</span>;
      case 'FAULTED':
        return <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-rose-500/20 text-rose-300 border border-rose-500/40 animate-pulse">FAULTED</span>;
      case 'COMPLETED':
        return <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-emerald-500/20 text-emerald-300 border border-emerald-500/40">COMPLETED</span>;
      default:
        return <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-slate-700 text-slate-300">IDLE</span>;
    }
  };

  return (
    <div className="bg-[#0c1322] border border-slate-800 rounded-xl p-4 shadow-xl">
      <div className="flex items-center justify-between pb-3 border-b border-slate-800">
        <div className="flex items-center space-x-2">
          <Bot className="w-4 h-4 text-cyan-400" />
          <h3 className="font-semibold text-slate-200 text-sm">AGV Fleet Telemetry</h3>
        </div>
        <span className="text-xs font-mono text-slate-400">
          Online: {robotList.length}
        </span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mt-3">
        {robotList.map((robot) => {
          const isSelected = selectedRobotId === robot.id;
          return (
            <div
              key={robot.id}
              onClick={() => onSelectRobot(isSelected ? null : robot.id)}
              className={`p-3 rounded-lg border transition-all cursor-pointer ${
                isSelected
                  ? 'bg-slate-800/80 border-cyan-500 shadow-md shadow-cyan-500/10'
                  : 'bg-slate-900/50 border-slate-800/80 hover:border-slate-700'
              }`}
            >
              <div className="flex items-center justify-between">
                <span className="font-mono font-bold text-slate-100 text-sm">
                  {robot.id}
                </span>
                {getStatusBadge(robot.status)}
              </div>

              {/* Coordinates & Battery */}
              <div className="mt-2.5 flex items-center justify-between text-xs text-slate-400">
                <div className="flex items-center space-x-1 font-mono">
                  <Navigation className="w-3 h-3 text-cyan-400" />
                  <span>({robot.position.x}, {robot.position.y})</span>
                </div>
                <div className="flex items-center space-x-1">
                  <Battery className="w-3 h-3 text-emerald-400" />
                  <span className="font-mono">{robot.battery_level.toFixed(0)}%</span>
                </div>
              </div>

              {/* Stats Counters */}
              <div className="mt-2 pt-2 border-t border-slate-800/60 grid grid-cols-3 gap-1 text-[11px] text-slate-400">
                <div>
                  <span className="block text-[10px] text-slate-500">Dist</span>
                  <span className="font-mono text-slate-200 font-semibold">{robot.distance_travelled}m</span>
                </div>
                <div>
                  <span className="block text-[10px] text-slate-500">Tasks</span>
                  <span className="font-mono text-slate-200 font-semibold">{robot.tasks_completed}</span>
                </div>
                <div>
                  <span className="block text-[10px] text-slate-500">Wait</span>
                  <span className="font-mono text-slate-200 font-semibold">{robot.total_waiting_time}t</span>
                </div>
              </div>

              {/* Active Task or Fault banner */}
              {robot.task_id && (
                <div className="mt-2 text-[10px] bg-cyan-950/40 border border-cyan-800/50 text-cyan-300 px-2 py-1 rounded truncate">
                  Task: {robot.task_id}
                </div>
              )}

              {robot.status === 'FAULTED' && (
                <div className="mt-2 text-[10px] bg-rose-950/40 border border-rose-800/50 text-rose-300 px-2 py-1 rounded flex items-center justify-between">
                  <span className="truncate">{robot.current_fault || 'Fault'}</span>
                </div>
              )}

              {/* Fault simulation actions */}
              <div className="mt-2.5 pt-2 border-t border-slate-800/40 flex items-center justify-end space-x-2">
                {robot.status === 'FAULTED' ? (
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      onRecoverRobot(robot.id);
                    }}
                    className="px-2 py-0.5 rounded text-[10px] bg-emerald-600 hover:bg-emerald-500 text-white font-medium transition-colors"
                  >
                    Recover
                  </button>
                ) : (
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      onTriggerFault(robot.id);
                    }}
                    className="px-2 py-0.5 rounded text-[10px] bg-rose-900/60 hover:bg-rose-800 text-rose-200 border border-rose-700/60 transition-colors"
                  >
                    Inject Fault
                  </button>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
