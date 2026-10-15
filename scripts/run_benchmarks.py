"""
FactoryTwin - Headless Benchmarking & Evaluation Suite
Executes reproducible simulation trials comparing FIFO and Nearest Robot scheduling
across varying obstacle densities, fleet sizes, and task congestion.
Exports output to benchmark_results.csv.
"""

import sys
import os
import csv
import time
from pathlib import Path

# Ensure backend package is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from app.api.benchmarks import run_benchmark_trial
from app.simulation.scheduler import SchedulingPolicy


def main():
    print("=" * 80)
    print(" FactoryTwin - Industrial Simulation & Scheduler Benchmarking Suite")
    print("=" * 80)

    output_csv = Path(__file__).resolve().parent.parent / "benchmark_results.csv"

    benchmarks_config = [
        {"scenario": "Standard 3-AGV Facility", "num_robots": 3, "num_tasks": 6, "max_ticks": 200, "seed": 42},
        {"scenario": "Congested Fleet (4-AGVs, 8 Tasks)", "num_robots": 4, "num_tasks": 8, "max_ticks": 220, "seed": 101},
        {"scenario": "High Load Demand (4-AGVs, 12 Tasks)", "num_robots": 4, "num_tasks": 12, "max_ticks": 260, "seed": 202},
        {"scenario": "Constrained Fleet (2-AGVs, 6 Tasks)", "num_robots": 2, "num_tasks": 6, "max_ticks": 220, "seed": 303},
    ]

    all_results = []
    policies = [SchedulingPolicy.FIFO, SchedulingPolicy.NEAREST_ROBOT]

    print(f"\nRunning {len(benchmarks_config) * len(policies)} headless benchmark trials...\n")
    print(f"{'Scenario':<34} | {'Policy':<14} | {'Comp%':<6} | {'AvgDeliv':<9} | {'Dist':<6} | {'Replans':<7} | {'Collisions'}")
    print("-" * 96)

    for cfg in benchmarks_config:
        for pol in policies:
            res = run_benchmark_trial(
                policy=pol,
                scenario_name=cfg["scenario"],
                num_robots=cfg["num_robots"],
                num_tasks=cfg["num_tasks"],
                max_ticks=cfg["max_ticks"],
                seed=cfg["seed"],
            )
            all_results.append(res)
            print(
                f"{res['scenario']:<34} | {res['policy']:<14} | {res['completion_rate_pct']:>5.1f}% | "
                f"{res['avg_delivery_time']:>7.1f}t | {res['total_distance']:>4} | {res['replans_count']:>5}   | {res['actual_collisions']}"
            )

    # Export to CSV
    fieldnames = [
        "scenario", "policy", "num_robots", "num_tasks", "ticks_executed",
        "tasks_completed", "tasks_failed", "completion_rate_pct", "total_distance",
        "total_waiting_time", "throughput_per_100_ticks", "avg_delivery_time",
        "replans_count", "conflicts_prevented", "actual_collisions"
    ]

    with open(output_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in all_results:
            writer.writerow(r)

    print("-" * 96)
    print(f"\n[OK] Benchmarking complete. Exported {len(all_results)} trials to {output_csv}")
    
    # Summary Insights
    fifo_deliveries = [r["avg_delivery_time"] for r in all_results if r["policy"] == "FIFO" and r["avg_delivery_time"] > 0]
    near_deliveries = [r["avg_delivery_time"] for r in all_results if r["policy"] == "NEAREST_ROBOT" and r["avg_delivery_time"] > 0]
    
    if fifo_deliveries and near_deliveries:
        avg_fifo = sum(fifo_deliveries) / len(fifo_deliveries)
        avg_near = sum(near_deliveries) / len(near_deliveries)
        print(f"Summary Delivery Time: FIFO = {avg_fifo:.1f} ticks vs Nearest Robot = {avg_near:.1f} ticks")


if __name__ == "__main__":
    main()
