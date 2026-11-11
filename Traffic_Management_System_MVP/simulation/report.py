"""Summary report generation for completed or ongoing simulation runs."""

import json
from datetime import datetime
from pathlib import Path


def build_summary_report(engine):
    """Build a summary report from the current simulation engine state."""

    scenario = engine.scenario
    metrics = engine.metrics
    signals = engine.signals

    strategy = "Adaptive" if signals.adaptive else "Fixed-time"

    return {
        "report_generated_at": datetime.now().astimezone().isoformat(
            timespec="seconds"
        ),
        "scenario": {
            "name": scenario.name,
            "intersections": [item.id for item in scenario.intersections],
            "roads": [road.id for road in scenario.roads],
        },
        "control_strategy": {
            "type": strategy,
            "emergency_priority_active": (
                signals.priority_direction is not None
            ),
            "emergency_priority_direction": signals.priority_direction,
        },
        "simulation": {
            "state": engine.state,
            "duration_seconds": round(engine.clock, 2),
            "ticks": engine.tick_count,
            "signal_phase": signals.phase,
        },
        "traffic_metrics": {
            "vehicles_spawned": metrics.spawned,
            "vehicles_completed": metrics.completed,
            "vehicles_active": len(engine.traffic.vehicles),
            "throughput_per_minute": round(
                metrics.throughput_per_minute, 2
            ),
            "average_wait_seconds": round(
                metrics.average_wait_seconds, 2
            ),
            "total_wait_seconds": round(
                metrics.total_wait_seconds, 2
            ),
        },
    }


def save_summary_report(engine, output_dir="reports"):
    """Generate and save a timestamped JSON summary report."""

    report = build_summary_report(engine)

    directory = Path(output_dir)
    directory.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"summary_report_{timestamp}.json"
    output_path = directory / filename

    with output_path.open("w", encoding="utf-8") as file:
        json.dump(report, file, indent=4, ensure_ascii=False)

    return output_path