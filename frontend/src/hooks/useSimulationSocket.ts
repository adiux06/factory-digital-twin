import { useEffect, useRef, useState, useCallback } from 'react';
import type { SimulationState, SimulationEvent } from '../types';
import { api } from '../services/api';

export function useSimulationSocket(simId: string | null) {
  const [state, setState] = useState<SimulationState | null>(null);
  const [isConnected, setIsConnected] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [eventFeed, setEventFeed] = useState<SimulationEvent[]>([]);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const connect = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.close();
    }

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const isLocal = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';
    const host = isLocal ? `${window.location.hostname}:8000` : window.location.host;
    const targetSimId = simId || 'default';
    const wsUrl = `${protocol}//${host}/ws/simulations/${targetSimId}`;

    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      setIsConnected(true);
      setError(null);
    };

    ws.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data);
        if (payload.category === 'simulation.state' && payload.state) {
          setState(payload.state);
        } else if (payload.category && payload.message) {
          setEventFeed((prev) => [
            {
              tick: payload.tick ?? 0,
              event_type: payload.category,
              message: payload.message,
              data: payload.data || {},
            },
            ...prev.slice(0, 49),
          ]);
        }
      } catch (err) {
        console.error('Failed to parse WS message', err);
      }
    };

    ws.onerror = () => {
      setError('Live WebSocket connection disrupted. Attempting reconnection...');
    };

    ws.onclose = () => {
      setIsConnected(false);
      reconnectTimeoutRef.current = setTimeout(() => {
        connect();
      }, 2000);
    };
  }, [simId]);

  useEffect(() => {
    let isCurrent = true;
    const targetId = simId || 'default';
    api.getSimulation(targetId)
      .then((data) => {
        if (isCurrent && data) {
          setState((prev) => prev || data);
        }
      })
      .catch(() => {});
    return () => {
      isCurrent = false;
    };
  }, [simId]);

  useEffect(() => {
    connect();
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
    };
  }, [connect]);

  useEffect(() => {
    if (isConnected || !simId) return;
    const interval = setInterval(async () => {
      try {
        const data = await api.getSimulation(simId);
        setState(data);
      } catch {
        // silent fallback
      }
    }, 1000);
    return () => clearInterval(interval);
  }, [isConnected, simId]);

  const sendCommand = (action: string, value?: any) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ action, value }));
    }
  };

  return {
    state,
    setState,
    isConnected,
    error,
    eventFeed,
    sendCommand,
    reconnect: connect,
  };
}
