from __future__ import annotations
import asyncio
import uuid
from datetime import datetime
from typing import Dict, List, Optional
from app.simulation.grid import GridMap, Position
from app.simulation.engine import SimulationEngine
from app.simulation.scheduler import SchedulingPolicy
from app.simulation.task import Task, TaskPriority, TaskStatus
from app.inspection.pipeline import VisionInspectionEngine
from app.db.session import SessionLocal
from app.db.models import SimulationRunRecord, TaskRecord, InspectionRecord


class ManagedSimulation:
    def __init__(
        self,
        simulation_id: str,
        engine: SimulationEngine,
        speed_multiplier: float = 1.0,
    ):
        self.id = simulation_id
        self.engine = engine
        self.speed_multiplier = speed_multiplier
        self.loop_task: Optional[asyncio.Task] = None
        self.subscribers: List[asyncio.Queue] = []
        self.inspection_engine = VisionInspectionEngine()

        # Connect engine event listener to broadcast queue
        self.engine.register_event_listener(self._on_engine_event)

    def _on_engine_event(self, event) -> None:
        # Check if inspection was queued
        if event.event_type == "inspection.queued":
            task_id = event.data.get("task_id")
            if task_id and task_id in self.engine.tasks:
                task = self.engine.tasks[task_id]
                # Auto-run inspection with reference dataset sample
                self._run_task_inspection(task)

        # Notify any subscribed WebSockets
        payload = {
            "category": event.event_type,
            "tick": event.tick,
            "message": event.message,
            "data": event.data,
            "timestamp": datetime.utcnow().isoformat(),
        }
        for q in list(self.subscribers):
            try:
                q.put_nowait(payload)
            except Exception:
                pass

    def _run_task_inspection(self, task: Task) -> None:
        """Runs the genuine vision inspection for delivered sample item."""
        from app.core.config import DATASETS_DIR
        samples_dir = DATASETS_DIR / "inspection" / "samples"
        
        sample_path = None
        # Select sample image if available
        if samples_dir.exists():
            defect_samples = list(samples_dir.glob("sample_defect_*.png"))
            normal_samples = list(samples_dir.glob("sample_normal_*.png"))
            all_samples = defect_samples + normal_samples
            if all_samples:
                import random
                sample_path = random.choice(all_samples)

        if sample_path and sample_path.exists():
            result = self.inspection_engine.analyze_file(sample_path)
        else:
            # Fallback to generating a sample part
            from PIL import Image
            test_img = np.zeros((256, 256, 3), dtype=np.uint8)
            result = self.inspection_engine.inspect_image(test_img)

        # Update task status based on genuine prediction
        if result.prediction == "ACCEPTABLE":
            task.status = TaskStatus.COMPLETED
            task.mark_completed(self.engine.tick)
            self.engine.metrics.tasks_completed += 1
        else:
            task.status = TaskStatus.FAILED
            task.failure_reason = f"Rejected at QC: {result.prediction} ({result.defect_type})"
            self.engine.metrics.tasks_failed += 1

        # Release robot from inspection
        if task.assigned_robot_id and task.assigned_robot_id in self.engine.robots:
            robot = self.engine.robots[task.assigned_robot_id]
            robot.tasks_completed += 1
            robot.set_state(Robot.status if hasattr(robot, 'status') else "IDLE")  # recovers to IDLE
            from app.simulation.robot import RobotState
            robot.status = RobotState.IDLE
            robot.task_id = None
            self.engine.robot_task_stage.pop(robot.id, None)

        self.engine.emit_event(
            "inspection.completed",
            f"Quality Inspection finished for {task.id}: {result.prediction} (Confidence: {result.confidence})",
            {
                "task_id": task.id,
                "prediction": result.prediction,
                "confidence": result.confidence,
                "anomaly_score": result.anomaly_score,
                "defect_type": result.defect_type,
                "defect_count": result.defect_count,
                "inference_time_ms": result.inference_time_ms,
                "annotated_image_b64": result.annotated_image_b64,
            },
        )

        # Persist inspection record to SQLite
        try:
            with SessionLocal() as db:
                rec = InspectionRecord(
                    id=f"INSP-{uuid.uuid4().hex[:8].upper()}",
                    run_id=self.id,
                    task_id=task.id,
                    sample_id=sample_path.name if sample_path else "synthetic",
                    prediction=result.prediction,
                    confidence=result.confidence,
                    anomaly_score=result.anomaly_score,
                    defect_type=result.defect_type,
                    defect_count=result.defect_count,
                    max_defect_area_px=result.max_defect_area_px,
                    inference_time_ms=result.inference_time_ms,
                )
                db.add(rec)
                db.commit()
        except Exception:
            pass

    async def run_loop(self) -> None:
        while self.engine.is_running:
            self.engine.step()
            # Broadcast state
            state_event = {
                "category": "simulation.state",
                "tick": self.engine.tick,
                "state": self.engine.get_state(),
                "timestamp": datetime.utcnow().isoformat(),
            }
            for q in list(self.subscribers):
                try:
                    q.put_nowait(state_event)
                except Exception:
                    pass

            delay = max(0.05, 0.25 / self.speed_multiplier)
            await asyncio.sleep(delay)


class SimulationManager:
    _instance: Optional[SimulationManager] = None

    def __init__(self):
        self.simulations: Dict[str, ManagedSimulation] = {}

    @classmethod
    def get_instance(cls) -> SimulationManager:
        if cls._instance is None:
            cls._instance = SimulationManager()
        return cls._instance

    def create_simulation(
        self,
        scheduling_policy: SchedulingPolicy = SchedulingPolicy.NEAREST_ROBOT,
        num_robots: int = 3,
        scenario_id: str = "default_factory",
    ) -> ManagedSimulation:
        if isinstance(scheduling_policy, str):
            scheduling_policy = SchedulingPolicy(scheduling_policy)
        sim_id = str(uuid.uuid4())
        grid = GridMap.create_default_factory()
        engine = SimulationEngine(grid=grid, scheduling_policy=scheduling_policy)

        # Spawn initial robots at charging pads/docks
        dock_positions = [
            Position(x=4, y=13),
            Position(x=6, y=13),
            Position(x=14, y=13),
            Position(x=16, y=13),
            Position(x=2, y=13),
            Position(x=18, y=13),
        ]
        for i in range(min(num_robots, len(dock_positions))):
            engine.add_robot(f"AGV-{i+1:02d}", dock_positions[i])

        # Prepopulate demo tasks
        demo_tasks = [
            Task(
                id="TASK-01",
                pickup_location=Position(x=1, y=2),   # PICKUP_A
                destination=Position(x=9, y=3),      # WS_ASSEMBLY_1
                priority=TaskPriority.HIGH,
                item_type="Hydraulic Cylinder",
            ),
            Task(
                id="TASK-02",
                pickup_location=Position(x=1, y=6),   # PICKUP_B
                destination=Position(x=10, y=12),    # QC_INSPECTION_1
                priority=TaskPriority.CRITICAL,
                requires_inspection=True,
                item_type="Machined Flange",
            ),
            Task(
                id="TASK-03",
                pickup_location=Position(x=1, y=10),  # PICKUP_C
                destination=Position(x=18, y=2),     # BAY_OUT_1
                priority=TaskPriority.MEDIUM,
                item_type="Bearing Housing",
            ),
        ]
        for t in demo_tasks:
            engine.add_task(t)

        sim = ManagedSimulation(simulation_id=sim_id, engine=engine)
        self.simulations[sim_id] = sim

        # Persist run to SQLite
        try:
            with SessionLocal() as db:
                run_rec = SimulationRunRecord(
                    id=sim_id,
                    scenario_id=scenario_id,
                    policy=scheduling_policy.value if hasattr(scheduling_policy, "value") else str(scheduling_policy),
                    status="CREATED",
                )
                db.add(run_rec)
                db.commit()
        except Exception:
            pass

        return sim

    def get_simulation(self, sim_id: str) -> Optional[ManagedSimulation]:
        return self.simulations.get(sim_id)

    def start_simulation(self, sim_id: str) -> bool:
        sim = self.get_simulation(sim_id)
        if not sim or sim.engine.is_running:
            return False

        sim.engine.is_running = True
        sim.loop_task = asyncio.create_task(sim.run_loop())
        sim.engine.emit_event("simulation.started", f"Simulation {sim_id} started")
        return True

    def pause_simulation(self, sim_id: str) -> bool:
        sim = self.get_simulation(sim_id)
        if not sim or not sim.engine.is_running:
            return False

        sim.engine.is_running = False
        if sim.loop_task:
            sim.loop_task.cancel()
            sim.loop_task = None
        sim.engine.emit_event("simulation.paused", f"Simulation {sim_id} paused")
        return True

    def step_simulation(self, sim_id: str) -> bool:
        sim = self.get_simulation(sim_id)
        if not sim:
            return False
        sim.engine.step()
        return True

    def reset_simulation(self, sim_id: str) -> bool:
        sim = self.get_simulation(sim_id)
        if not sim:
            return False
        if sim.engine.is_running:
            self.pause_simulation(sim_id)
        sim.engine.reset()
        sim.engine.emit_event("simulation.reset", f"Simulation {sim_id} reset to tick 0")
        return True


simulation_manager = SimulationManager.get_instance()
