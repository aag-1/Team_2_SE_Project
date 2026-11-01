"""Congestion detection (TMS-F-010, TC-CON-01).

Congestion = queue length or average wait exceeds configured thresholds.
Thresholds live in data/scenarios.json -> simulation.thresholds.
"""
from __future__ import annotations

DEFAULT_THRESHOLDS = {
    "queue_length": 12,
    "avg_wait_seconds": 15.0,
    "active_vehicles": 40,
}


def is_congested(queue_length: int, avg_wait_seconds: float,
                 active_vehicles: int = 0,
                 thresholds: dict | None = None) -> tuple[bool, str]:
    """Return (congested, reason). Pure function for testability."""
    th = dict(DEFAULT_THRESHOLDS)
    if thresholds:
        th.update(thresholds)
    if queue_length >= th["queue_length"]:
        return True, f"queue {queue_length} >= {th['queue_length']}"
    if avg_wait_seconds >= th["avg_wait_seconds"]:
        return True, f"avg_wait {avg_wait_seconds:.1f}s >= {th['avg_wait_seconds']}s"
    if active_vehicles and active_vehicles >= th["active_vehicles"]:
        return True, f"active {active_vehicles} >= {th['active_vehicles']}"
    return False, ""


def status_label(queue_length: int, avg_wait_seconds: float,
                 active_vehicles: int = 0,
                 thresholds: dict | None = None) -> str:
    congested, _ = is_congested(queue_length, avg_wait_seconds, active_vehicles, thresholds)
    return "CONGESTED" if congested else "FLOW OK"
