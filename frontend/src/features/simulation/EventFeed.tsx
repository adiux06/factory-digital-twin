import React, { useState } from 'react';
import type { SimulationEvent } from '../../types';
import { Activity, ShieldAlert, Bot, Package, Microscope } from 'lucide-react';

interface EventFeedProps {
  events: SimulationEvent[];
}

export const EventFeed: React.FC<EventFeedProps> = ({ events }) => {
  const [filter, setFilter] = useState<string>('ALL');

  const filteredEvents = events.filter((e) => {
    if (filter === 'ALL') return true;
    if (filter === 'CONFLICT' && (e.event_type.includes('conflict') || e.event_type.includes('obstacle'))) return true;
    if (filter === 'TASK' && e.event_type.includes('task')) return true;
    if (filter === 'INSPECTION' && e.event_type.includes('inspection')) return true;
    if (filter === 'ROBOT' && e.event_type.includes('robot')) return true;
    return false;
  });

  const getEventIcon = (type: string) => {
    if (type.includes('conflict') || type.includes('collision') || type.includes('obstacle') || type.includes('fault')) {
      return <ShieldAlert className="w-3.5 h-3.5 text-rose-400" />;
    }
    if (type.includes('inspection')) {
      return <Microscope className="w-3.5 h-3.5 text-purple-400" />;
    }
    if (type.includes('task')) {
      return <Package className="w-3.5 h-3.5 text-cyan-400" />;
    }
    return <Bot className="w-3.5 h-3.5 text-slate-400" />;
  };

  return (
    <div className="bg-[#0c1322] border border-slate-800 rounded-xl p-4 shadow-xl flex flex-col h-full">
      <div className="flex items-center justify-between pb-3 border-b border-slate-800">
        <div className="flex items-center space-x-2">
          <Activity className="w-4 h-4 text-cyan-400" />
          <h3 className="font-semibold text-slate-200 text-sm">Live Simulation Telemetry Stream</h3>
        </div>

        {/* Filter buttons */}
        <div className="flex items-center space-x-1 text-[10px]">
          {['ALL', 'TASK', 'ROBOT', 'CONFLICT', 'INSPECTION'].map((f) => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={`px-2 py-0.5 rounded transition-colors ${
                filter === f
                  ? 'bg-slate-700 text-cyan-300 font-semibold'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              {f}
            </button>
          ))}
        </div>
      </div>

      <div className="mt-3 flex-1 overflow-y-auto space-y-1.5 pr-1 max-h-[360px]">
        {filteredEvents.length === 0 ? (
          <div className="text-center py-8 text-slate-500 text-xs">
            Waiting for simulation ticks and navigation events...
          </div>
        ) : (
          filteredEvents.map((e, idx) => (
            <div
              key={idx}
              className="p-2 rounded bg-slate-900/40 border border-slate-850 hover:border-slate-800 text-xs flex items-start space-x-2 transition-colors"
            >
              <div className="mt-0.5">{getEventIcon(e.event_type)}</div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between">
                  <span className="font-mono text-[10px] text-cyan-400 font-medium">
                    TICK {e.tick.toString().padStart(3, '0')}
                  </span>
                  <span className="text-[10px] text-slate-500 font-mono">
                    {e.event_type}
                  </span>
                </div>
                <p className="text-slate-300 text-[11px] mt-0.5 leading-tight">{e.message}</p>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
};
