const API_BASE = '/api';

export const api = {
  async getHealth() {
    const res = await fetch(`${API_BASE}/health`);
    return res.json();
  },

  async getScenarios() {
    const res = await fetch(`${API_BASE}/simulations/scenarios`);
    return res.json();
  },

  async createSimulation(policy = 'NEAREST_ROBOT', numRobots = 3, scenarioId = 'default_factory') {
    const res = await fetch(`${API_BASE}/simulations`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        scheduling_policy: policy,
        num_robots: numRobots,
        scenario_id: scenarioId,
      }),
    });
    return res.json();
  },

  async getSimulation(id: string) {
    const res = await fetch(`${API_BASE}/simulations/${id}`);
    if (!res.ok) throw new Error('Simulation not found');
    return res.json();
  },

  async startSimulation(id: string) {
    const res = await fetch(`${API_BASE}/simulations/${id}/start`, { method: 'POST' });
    return res.json();
  },

  async pauseSimulation(id: string) {
    const res = await fetch(`${API_BASE}/simulations/${id}/pause`, { method: 'POST' });
    return res.json();
  },

  async stepSimulation(id: string) {
    const res = await fetch(`${API_BASE}/simulations/${id}/step`, { method: 'POST' });
    return res.json();
  },

  async resetSimulation(id: string) {
    const res = await fetch(`${API_BASE}/simulations/${id}/reset`, { method: 'POST' });
    return res.json();
  },

  async setSpeed(id: string, multiplier: number) {
    const res = await fetch(`${API_BASE}/simulations/${id}/speed`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ speed_multiplier: multiplier }),
    });
    return res.json();
  },

  async createTask(id: string, data: {
    pickup_x: number;
    pickup_y: number;
    dest_x: number;
    dest_y: number;
    priority?: string;
    requires_inspection?: boolean;
    item_type?: string;
  }) {
    const res = await fetch(`${API_BASE}/simulations/${id}/tasks`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    return res.json();
  },

  async addObstacle(id: string, x: number, y: number, duration?: number) {
    const res = await fetch(`${API_BASE}/simulations/${id}/obstacles`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ x, y, duration_ticks: duration }),
    });
    return res.json();
  },

  async removeObstacle(id: string, obstacleId: string) {
    const res = await fetch(`${API_BASE}/simulations/${id}/obstacles/${obstacleId}`, {
      method: 'DELETE',
    });
    return res.json();
  },

  async triggerFault(id: string, robotId: string, reason = 'Motor drive stall') {
    const res = await fetch(`${API_BASE}/simulations/${id}/faults`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ robot_id: robotId, reason }),
    });
    return res.json();
  },

  async recoverRobot(id: string, robotId: string) {
    const res = await fetch(`${API_BASE}/simulations/${id}/recover`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ robot_id: robotId }),
    });
    return res.json();
  },

  async getInspectionSamples() {
    const res = await fetch(`${API_BASE}/inspection/samples`);
    return res.json();
  },

  async analyzeInspection(sampleId?: string, file?: File) {
    let url = `${API_BASE}/inspection/analyze`;
    if (sampleId) {
      url += `?sample_id=${encodeURIComponent(sampleId)}`;
      const res = await fetch(url, { method: 'POST' });
      return res.json();
    } else if (file) {
      const formData = new FormData();
      formData.append('file', file);
      const res = await fetch(url, {
        method: 'POST',
        body: formData,
      });
      return res.json();
    }
    throw new Error('Must provide either sampleId or file');
  },

  async getInspectionMetrics() {
    const res = await fetch(`${API_BASE}/inspection/metrics`);
    return res.json();
  },

  async getInspectionResults(limit = 20, offset = 0) {
    const res = await fetch(`${API_BASE}/inspection/results?limit=${limit}&offset=${offset}`);
    return res.json();
  },

  async runBenchmarks(numRobots = 3, numTasks = 6, maxTicks = 120, seed = 42) {
    const res = await fetch(`${API_BASE}/benchmarks/run`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ num_robots: numRobots, num_tasks: numTasks, max_ticks: maxTicks, seed }),
    });
    return res.json();
  },

  async getBenchmarkHistory() {
    const res = await fetch(`${API_BASE}/benchmarks`);
    return res.json();
  },
};
