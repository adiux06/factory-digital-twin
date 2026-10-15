import React, { useState } from 'react';
import type { Task, TaskPriority } from '../../types';
import { Package, Plus, Microscope, ArrowRight } from 'lucide-react';

interface TaskPanelProps {
  tasks: Record<string, Task>;
  onCreateTask: (taskData: {
    pickup_x: number;
    pickup_y: number;
    dest_x: number;
    dest_y: number;
    priority: TaskPriority;
    requires_inspection: boolean;
    item_type: string;
  }) => void;
}

export const TaskManagementPanel: React.FC<TaskPanelProps> = ({ tasks, onCreateTask }) => {
  const [isCreating, setIsCreating] = useState(false);
  const [pickupPreset, setPickupPreset] = useState('PICKUP_A');
  const [destPreset, setDestPreset] = useState('WS_ASSEMBLY_1');
  const [priority, setPriority] = useState<TaskPriority>('MEDIUM');
  const [requiresInspection, setRequiresInspection] = useState(false);
  const [itemType, setItemType] = useState('Machined Flange');

  const stationPresets: Record<string, { x: number; y: number; label: string }> = {
    PICKUP_A: { x: 1, y: 2, label: 'Raw Materials Intake A (1, 2)' },
    PICKUP_B: { x: 1, y: 6, label: 'Raw Materials Intake B (1, 6)' },
    PICKUP_C: { x: 1, y: 10, label: 'Raw Materials Intake C (1, 10)' },
    WS_ASSEMBLY_1: { x: 9, y: 3, label: 'Assembly Cell 1 (9, 3)' },
    WS_ASSEMBLY_2: { x: 10, y: 3, label: 'Assembly Cell 2 (10, 3)' },
    WS_PACKING_1: { x: 9, y: 8, label: 'Packing Cell 1 (9, 8)' },
    QC_INSPECTION_1: { x: 10, y: 12, label: 'QC Vision Inspection Bay (10, 12)' },
    BAY_OUT_1: { x: 18, y: 2, label: 'Outbound Bay 1 (18, 2)' },
    BAY_OUT_2: { x: 18, y: 6, label: 'Outbound Bay 2 (18, 6)' },
    BAY_OUT_3: { x: 18, y: 10, label: 'Outbound Bay 3 (18, 10)' },
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const p = stationPresets[pickupPreset];
    const d = stationPresets[destPreset];
    onCreateTask({
      pickup_x: p.x,
      pickup_y: p.y,
      dest_x: d.x,
      dest_y: d.y,
      priority,
      requires_inspection: requiresInspection || destPreset === 'QC_INSPECTION_1',
      item_type: itemType,
    });
    setIsCreating(false);
  };

  const taskList = Object.values(tasks).reverse();

  const getPriorityBadge = (p: TaskPriority) => {
    switch (p) {
      case 'CRITICAL':
        return <span className="text-[10px] bg-rose-500/20 text-rose-300 border border-rose-500/40 px-1.5 py-0.5 rounded font-bold">CRITICAL</span>;
      case 'HIGH':
        return <span className="text-[10px] bg-amber-500/20 text-amber-300 border border-amber-500/40 px-1.5 py-0.5 rounded font-semibold">HIGH</span>;
      case 'MEDIUM':
        return <span className="text-[10px] bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 px-1.5 py-0.5 rounded">MEDIUM</span>;
      default:
        return <span className="text-[10px] bg-slate-700 text-slate-400 px-1.5 py-0.5 rounded">LOW</span>;
    }
  };

  return (
    <div className="bg-[#0c1322] border border-slate-800 rounded-xl p-4 shadow-xl flex flex-col h-full">
      <div className="flex items-center justify-between pb-3 border-b border-slate-800">
        <div className="flex items-center space-x-2">
          <Package className="w-4 h-4 text-cyan-400" />
          <h3 className="font-semibold text-slate-200 text-sm">Production Tasks</h3>
          <span className="text-xs bg-slate-800 text-slate-400 px-2 py-0.5 rounded-full font-mono">
            {taskList.length}
          </span>
        </div>
        <button
          onClick={() => setIsCreating(!isCreating)}
          className="flex items-center space-x-1 text-xs bg-cyan-600 hover:bg-cyan-500 text-white font-medium px-2.5 py-1 rounded transition-colors"
        >
          <Plus className="w-3.5 h-3.5" />
          <span>New Task</span>
        </button>
      </div>

      {/* Task Creation Form Drawer */}
      {isCreating && (
        <form onSubmit={handleSubmit} className="mt-3 p-3 bg-slate-900/80 border border-cyan-900/60 rounded-lg text-xs space-y-2.5">
          <div className="font-semibold text-cyan-400 text-xs">Create Factory Work Order</div>
          <div>
            <label className="block text-[11px] text-slate-400 mb-1">Material / Item Type</label>
            <select
              value={itemType}
              onChange={(e) => setItemType(e.target.value)}
              className="w-full bg-slate-850 border border-slate-750 rounded p-1.5 text-slate-200 text-xs focus:outline-none focus:border-cyan-500"
            >
              <option value="Machined Flange">Machined Flange (Auto QC Compatible)</option>
              <option value="Hydraulic Cylinder">Hydraulic Cylinder</option>
              <option value="Bearing Housing">Bearing Housing</option>
              <option value="Turbine Impeller">Turbine Impeller</option>
            </select>
          </div>

          <div className="grid grid-cols-2 gap-2">
            <div>
              <label className="block text-[11px] text-slate-400 mb-1">Pickup Station</label>
              <select
                value={pickupPreset}
                onChange={(e) => setPickupPreset(e.target.value)}
                className="w-full bg-slate-850 border border-slate-750 rounded p-1.5 text-slate-200 text-xs focus:outline-none focus:border-cyan-500"
              >
                <option value="PICKUP_A">Intake A (1, 2)</option>
                <option value="PICKUP_B">Intake B (1, 6)</option>
                <option value="PICKUP_C">Intake C (1, 10)</option>
              </select>
            </div>
            <div>
              <label className="block text-[11px] text-slate-400 mb-1">Destination Station</label>
              <select
                value={destPreset}
                onChange={(e) => {
                  setDestPreset(e.target.value);
                  if (e.target.value === 'QC_INSPECTION_1') setRequiresInspection(true);
                }}
                className="w-full bg-slate-850 border border-slate-750 rounded p-1.5 text-slate-200 text-xs focus:outline-none focus:border-cyan-500"
              >
                <option value="WS_ASSEMBLY_1">Assembly 1 (9, 3)</option>
                <option value="WS_ASSEMBLY_2">Assembly 2 (10, 3)</option>
                <option value="WS_PACKING_1">Packing (9, 8)</option>
                <option value="QC_INSPECTION_1">QC Vision Bay (10, 12)</option>
                <option value="BAY_OUT_1">Shipping Bay 1 (18, 2)</option>
                <option value="BAY_OUT_2">Shipping Bay 2 (18, 6)</option>
              </select>
            </div>
          </div>

          <div className="flex items-center justify-between pt-1">
            <div className="flex items-center space-x-2">
              <label className="text-[11px] text-slate-400">Priority:</label>
              <select
                value={priority}
                onChange={(e) => setPriority(e.target.value as TaskPriority)}
                className="bg-slate-850 border border-slate-750 rounded px-2 py-1 text-slate-200 text-xs"
              >
                <option value="LOW">LOW</option>
                <option value="MEDIUM">MEDIUM</option>
                <option value="HIGH">HIGH</option>
                <option value="CRITICAL">CRITICAL</option>
              </select>
            </div>

            <label className="flex items-center space-x-1.5 cursor-pointer text-[11px] text-slate-300">
              <input
                type="checkbox"
                checked={requiresInspection}
                onChange={(e) => setRequiresInspection(e.target.checked)}
                className="rounded border-slate-700 text-cyan-600 focus:ring-0"
              />
              <span className="flex items-center space-x-1">
                <Microscope className="w-3.5 h-3.5 text-purple-400" />
                <span>Require AI QC</span>
              </span>
            </label>
          </div>

          <div className="flex justify-end space-x-2 pt-1">
            <button
              type="button"
              onClick={() => setIsCreating(false)}
              className="px-2.5 py-1 text-slate-400 hover:text-slate-200"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="bg-cyan-600 hover:bg-cyan-500 text-white font-medium px-3 py-1 rounded transition-colors"
            >
              Dispatch Task
            </button>
          </div>
        </form>
      )}

      {/* Task List */}
      <div className="mt-3 flex-1 overflow-y-auto space-y-2 pr-1 max-h-[360px]">
        {taskList.length === 0 ? (
          <div className="text-center py-8 text-slate-500 text-xs">
            No tasks queued. Dispatch a work order above.
          </div>
        ) : (
          taskList.map((task) => (
            <div
              key={task.id}
              className="p-2.5 rounded-lg border border-slate-850 bg-slate-900/40 hover:border-slate-750 transition-colors text-xs"
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-1.5">
                  <span className="font-mono font-semibold text-slate-200">{task.id}</span>
                  {getPriorityBadge(task.priority)}
                </div>
                <span
                  className={`px-1.5 py-0.5 rounded text-[10px] font-medium font-mono ${
                    task.status === 'COMPLETED'
                      ? 'bg-emerald-500/20 text-emerald-400'
                      : task.status === 'FAILED'
                      ? 'bg-rose-500/20 text-rose-400'
                      : task.status === 'DELIVERING'
                      ? 'bg-cyan-500/20 text-cyan-400 animate-pulse'
                      : 'bg-amber-500/20 text-amber-400'
                  }`}
                >
                  {task.status}
                </span>
              </div>

              <div className="mt-1.5 text-slate-300 font-medium text-[11px] flex items-center justify-between">
                <span>{task.item_type}</span>
                {task.requires_inspection && (
                  <span className="flex items-center text-[10px] text-purple-400 space-x-0.5">
                    <Microscope className="w-3 h-3" />
                    <span>AI QC Required</span>
                  </span>
                )}
              </div>

              <div className="mt-1 flex items-center space-x-1 text-[11px] text-slate-400 font-mono">
                <span>({task.pickup_location.x}, {task.pickup_location.y})</span>
                <ArrowRight className="w-3 h-3 text-slate-600" />
                <span>({task.destination.x}, {task.destination.y})</span>
                {task.assigned_robot_id && (
                  <span className="ml-auto text-cyan-400 font-sans font-medium text-[10px]">
                    Assigned: {task.assigned_robot_id}
                  </span>
                )}
              </div>

              {task.failure_reason && (
                <div className="mt-1 text-[10px] text-rose-400 bg-rose-950/40 p-1 rounded">
                  {task.failure_reason}
                </div>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  );
};
