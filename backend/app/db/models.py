from datetime import datetime
from typing import Optional
from sqlalchemy import Column, Integer, Float, String, DateTime, Text, Boolean, ForeignKey
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class SimulationScenarioRecord(Base):
    __tablename__ = "simulation_scenarios"

    id = Column(String(50), primary_key=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    width = Column(Integer, default=20)
    height = Column(Integer, default=15)
    layout_json = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    runs = relationship("SimulationRunRecord", back_populates="scenario", cascade="all, delete-orphan")


class SimulationRunRecord(Base):
    __tablename__ = "simulation_runs"

    id = Column(String(50), primary_key=True)
    scenario_id = Column(String(50), ForeignKey("simulation_scenarios.id"), nullable=True)
    policy = Column(String(30), default="NEAREST_ROBOT")
    status = Column(String(30), default="CREATED")  # RUNNING, PAUSED, COMPLETED
    total_ticks = Column(Integer, default=0)
    tasks_completed = Column(Integer, default=0)
    tasks_failed = Column(Integer, default=0)
    total_distance = Column(Integer, default=0)
    total_wait_ticks = Column(Integer, default=0)
    replans_count = Column(Integer, default=0)
    conflicts_prevented = Column(Integer, default=0)
    actual_collisions = Column(Integer, default=0)
    throughput = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)
    finished_at = Column(DateTime, nullable=True)

    scenario = relationship("SimulationScenarioRecord", back_populates="runs")
    tasks = relationship("TaskRecord", back_populates="run", cascade="all, delete-orphan")
    inspections = relationship("InspectionRecord", back_populates="run", cascade="all, delete-orphan")


class TaskRecord(Base):
    __tablename__ = "task_records"

    id = Column(String(50), primary_key=True)
    run_id = Column(String(50), ForeignKey("simulation_runs.id"), nullable=True)
    item_type = Column(String(50), default="Standard Part")
    priority = Column(String(20), default="MEDIUM")
    pickup_x = Column(Integer, nullable=False)
    pickup_y = Column(Integer, nullable=False)
    dest_x = Column(Integer, nullable=False)
    dest_y = Column(Integer, nullable=False)
    status = Column(String(30), default="PENDING")
    assigned_robot = Column(String(50), nullable=True)
    created_at_tick = Column(Integer, default=0)
    completed_at_tick = Column(Integer, nullable=True)
    failure_reason = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    run = relationship("SimulationRunRecord", back_populates="tasks")


class InspectionRecord(Base):
    __tablename__ = "inspection_records"

    id = Column(String(50), primary_key=True)
    run_id = Column(String(50), ForeignKey("simulation_runs.id"), nullable=True)
    task_id = Column(String(50), nullable=True)
    sample_id = Column(String(100), nullable=True)
    prediction = Column(String(30), nullable=False)  # ACCEPTABLE, SUSPECTED DEFECT, INCONCLUSIVE
    confidence = Column(Float, nullable=False)
    anomaly_score = Column(Float, nullable=False)
    defect_type = Column(String(100), nullable=True)
    defect_count = Column(Integer, default=0)
    max_defect_area_px = Column(Float, default=0.0)
    inference_time_ms = Column(Float, nullable=False)
    image_path = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    run = relationship("SimulationRunRecord", back_populates="inspections")


class BenchmarkRecord(Base):
    __tablename__ = "benchmark_records"

    id = Column(String(50), primary_key=True)
    scenario_category = Column(String(50), nullable=False)
    scheduling_policy = Column(String(30), nullable=False)
    num_robots = Column(Integer, nullable=False)
    num_tasks = Column(Integer, nullable=False)
    total_ticks = Column(Integer, nullable=False)
    tasks_completed = Column(Integer, nullable=False)
    tasks_failed = Column(Integer, nullable=False)
    throughput = Column(Float, nullable=False)
    avg_delivery_time = Column(Float, nullable=False)
    total_distance = Column(Integer, nullable=False)
    replans_count = Column(Integer, default=0)
    conflicts_prevented = Column(Integer, default=0)
    actual_collisions = Column(Integer, default=0)
    seed = Column(Integer, default=42)
    created_at = Column(DateTime, default=datetime.utcnow)
