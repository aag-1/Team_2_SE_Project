
"""Simulation Engine: owns the master clock and the run-state controls.

Requirements covered:
  TMS-F-015  pause, resume, step and reset
  TMS-F-004  drives vehicle movement (via TrafficSimulation) under signal control
  TMS-F-013  prioritizes simulated emergency vehicles
  TMS-NF-008 adds timezone-aware timestamps to emitted events

Per the SAD, the engine advances discrete ticks and is independent of the
Dashboard UI. Interested components (dashboard, event logger) subscribe with
``add_listener(callback)``; callbacks receive ``(event_type, message, context)``.
"""
from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Any, Callable

from simulation.metrics import Metrics
from simulation.scenario import Scenario
from simulation.signals import DEFAULT_PHASE_SEQUENCE, SignalController
from simulation.traffic import TrafficSimulation

RUNNING = "RUNNING"
PAUSED = "PAUSED"
STEP_SECONDS = 1 / 30
MAX_TICK_SECONDS = 0.25

Listener = Callable[[str, str, dict], None]


class SimulationEngine:
    def __init__(self, scenario: Scenario, start_paused: bool = False):
        if not isinstance(scenario, Scenario):
            raise TypeError(
                "SimulationEngine requires a Scenario "
                "(use simulation.scenario.load_scenario/create_scenario)"
            )

        self.scenario = scenario
        cfg = scenario.simulation

        # Create the signal controller with optional adaptive settings.
        self.signals = SignalController(
            cfg["green_seconds"],
            cfg["amber_seconds"],
            cfg["red_clearance_seconds"],
            phase_sequence=tuple(
                cfg.get("phase_sequence", DEFAULT_PHASE_SEQUENCE)
            ),
            adaptive=cfg.get("adaptive_control", False),
            min_green_seconds=cfg.get("min_green_seconds", 6.0),
            max_green_seconds=cfg.get("max_green_seconds", 30.0),
        )

        self.metrics = Metrics()

        # Create traffic simulation with emergency vehicle support.
        self.traffic = TrafficSimulation(
            scenario.window["width"],
            scenario.window["height"],
            self.signals,
            self.metrics,
            cfg["vehicle_speed"],
            cfg["vehicle_length"],
            cfg["vehicle_gap"],
            cfg["spawn_interval_seconds"],
            seed=cfg.get("seed", 7),
            approaches=scenario.approaches,
            road_ids=scenario.road_ids,
            emergency_spawn_probability=cfg.get(
                "emergency_spawn_probability", 0.03
            ),
            emergency_priority_distance=cfg.get(
                "emergency_priority_distance", 210.0
            ),
        )

        self.state = PAUSED if start_paused else RUNNING
        self.clock = 0.0
        self.tick_count = 0
        self._listeners: list[Listener] = []

    # ------------------------------------------------------------ events

    def add_listener(self, callback: Listener) -> None:
        self._listeners.append(callback)

    @staticmethod
    def _current_timestamp() -> str:
        """Return the current timezone-aware ISO 8601 timestamp."""
        return datetime.now(timezone.utc).astimezone().isoformat(
            timespec="milliseconds"
        )

    def _emit(self, event_type: str, message: str, **context: Any) -> None:
        context.setdefault("sim_time", round(self.clock, 3))
        context["timestamp"] = self._current_timestamp()

        for callback in list(self._listeners):
            callback(event_type, message, context)

    # ------------------------------------------------------------ clock

    def _advance(self, dt: float) -> None:
        if (
            isinstance(dt, bool)
            or not isinstance(dt, (int, float))
            or not math.isfinite(dt)
            or dt <= 0
        ):
            raise ValueError(
                f"tick duration must be a positive finite number, got {dt!r}"
            )

        dt = min(float(dt), MAX_TICK_SECONDS)

        # Read current vehicle queues for each approach.
        queue_lengths = self.traffic.queue_lengths_by_direction()

        # Update signals using the current traffic demand.
        transition = self.signals.update(dt, queue_lengths)

        if transition:
            self._emit(
                "SIGNAL_CHANGE",
                f"Signal changed to {transition}",
                phase=transition,
            )

        # Update vehicle movement and detect approaching emergency vehicles.
        self.traffic.update(dt)

        self.clock += dt
        self.tick_count += 1

    def tick(self, dt: float) -> bool:
        """Advance by dt if running. Returns True if the clock advanced."""
        if self.state != RUNNING:
            return False

        self._advance(dt)
        return True

    # ------------------------------------------------------------ controls

    @property
    def paused(self) -> bool:
        return self.state == PAUSED

    def pause(self) -> None:
        if self.state != PAUSED:
            self.state = PAUSED
            self._emit("CONTROL", "Simulation paused")

    def resume(self) -> None:
        if self.state != RUNNING:
            self.state = RUNNING
            self._emit("CONTROL", "Simulation resumed")

    def toggle_pause(self) -> None:
        self.resume() if self.paused else self.pause()

    def step(self, dt: float = STEP_SECONDS) -> bool:
        """Advance exactly one tick while paused. Ignored while running."""
        if self.state != PAUSED:
            return False

        self._advance(dt)
        self._emit("CONTROL", f"Stepped {dt:.3f}s")
        return True

    def reset(self) -> None:
        """Return to the scenario's initial state; run/pause state is kept."""
        self.signals.reset()
        self.traffic.reset()

        self.traffic.spawn_interval = (
            self.scenario.simulation["spawn_interval_seconds"]
        )

        self.clock = 0.0
        self.tick_count = 0

        self._emit("CONTROL", "Simulation reset")

    def set_spawn_interval(self, seconds: float) -> float:
        self.traffic.spawn_interval = min(5.0, max(0.25, float(seconds)))
        return self.traffic.spawn_interval

    # ------------------------------------------------------------ state

    def snapshot(self) -> dict[str, Any]:
        """Current run state: compares runs and is saved as experiment results (TMS-F-017)."""
        m = self.metrics

        return {
            "scenario_name": self.scenario.name,
            "sim_time_seconds": round(self.clock, 6),
            "ticks": self.tick_count,
            "signal_phase": self.signals.phase,
            "vehicles_active": len(self.traffic.vehicles),
            "vehicles_spawned": m.spawned,
            "vehicles_completed": m.completed,
            "total_wait_seconds": round(m.total_wait_seconds, 6),
            "average_wait_seconds": round(m.average_wait_seconds, 6),
            "average_travel_time_seconds": round(m.average_travel_time_seconds, 6),
            "throughput_per_minute": round(m.throughput_per_minute, 6),
            "spawn_interval_seconds": self.traffic.spawn_interval,
        }
