export type RobotState =
  | 'IDLE'
  | 'ASSIGNED'
  | 'MOVING'
  | 'WAITING'
  | 'INSPECTING'
  | 'COMPLETED'
  | 'FAULTED';

export type TaskStatus =
  | 'PENDING'
  | 'ASSIGNED'
  | 'PICKING_UP'
  | 'DELIVERING'
  | 'INSPECTION_PENDING'
  | 'COMPLETED'
  | 'FAILED'
  | 'CANCELLED';

export type TaskPriority = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';

export type SchedulingPolicy = 'FIFO' | 'NEAREST_ROBOT';

export interface Position {
  x: number;
  y: number;
}

export interface Robot {
  id: string;
  position: Position;
  destination: Position | null;
  task_id: string | null;
  status: RobotState;
  planned_path: Position[];
  path_index: number;
  distance_travelled: number;
  tasks_completed: number;
  total_waiting_time: number;
  current_fault: string | null;
  battery_level: number;
}

export interface Task {
  id: string;
  pickup_location: Position;
  destination: Position;
  priority: TaskPriority;
  created_at_tick: number;
  status: TaskStatus;
  assigned_robot_id: string | null;
  completed_at_tick: number | null;
  failure_reason: string | null;
  requires_inspection: boolean;
  inspection_image_id: string | null;
  item_type: string;
}

export interface DynamicObstacle {
  id: string;
  x: number;
  y: number;
  created_at_tick: number;
  duration_ticks: number | null;
}

export interface GridMapData {
  width: number;
  height: number;
  static_obstacles: Position[];
  cell_types: Record<string, string>;
  workstations: Record<string, Position>;
  pickup_stations: Record<string, Position>;
  delivery_stations: Record<string, Position>;
  inspection_stations: Record<string, Position>;
  charging_stations: Record<string, Position>;
  dynamic_obstacles: DynamicObstacle[];
}

export interface SimulationMetrics {
  total_ticks: number;
  tasks_created: number;
  tasks_completed: number;
  tasks_failed: number;
  total_distance_travelled: number;
  total_wait_ticks: number;
  replans_count: number;
  conflicts_prevented: number;
  actual_collisions: number;
  throughput_per_100_ticks: number;
  avg_delivery_time_ticks: number;
}

export interface SimulationEvent {
  tick: number;
  event_type: string;
  message: string;
  data: Record<string, any>;
}

export interface SimulationState {
  tick: number;
  is_running: boolean;
  scheduling_policy: SchedulingPolicy;
  grid: GridMapData;
  robots: Record<string, Robot>;
  tasks: Record<string, Task>;
  metrics: SimulationMetrics;
  recent_events: SimulationEvent[];
}

export interface InspectionResult {
  prediction: 'ACCEPTABLE' | 'SUSPECTED DEFECT' | 'INCONCLUSIVE';
  confidence: number;
  anomaly_score: number;
  inference_time_ms: number;
  defect_type: string | null;
  defect_count: number;
  max_defect_area_px: number;
  annotated_image_b64: string | null;
  model_name: string;
  timestamp: number;
}

export interface EvaluationMetrics {
  precision: number;
  recall: number;
  f1_score: number;
  accuracy: number;
  true_positives: number;
  false_positives: number;
  true_negatives: number;
  false_negatives: number;
  mean_inference_time_ms: number;
  total_evaluated: number;
}

export interface SamplePart {
  id: string;
  filename: string;
  ground_truth: string;
  defect_type: string;
  split: string;
}

export interface BenchmarkTrial {
  scenario: string;
  policy: string;
  num_robots: number;
  num_tasks: number;
  ticks_executed: number;
  tasks_completed: number;
  tasks_failed: number;
  completion_rate_pct: number;
  total_distance: number;
  total_waiting_time: number;
  throughput_per_100_ticks: number;
  avg_delivery_time: number;
  replans_count: number;
  conflicts_prevented: number;
  actual_collisions: number;
}
