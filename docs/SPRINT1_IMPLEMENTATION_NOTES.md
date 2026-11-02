# Sprint 1 implementation notes: scenario management and core simulation

Owner: Aayush Gupta (PES2UG24CS018). Branch: `feature/aayush-sprint1-scenario-core`.
Work date: 2 November 2026. This is after the official Sprint 1 (19–23 Oct 2026) and
Sprint 2 (26–30 Oct 2026) windows; it is catch-up work, recorded with its real date.

This is a new supporting note. The submitted SRS, SAD and STP are unchanged.
Requirement IDs and test references follow the SRS.

## Sprint 1 status

| Issue | SRS ID | Test ref | Status | Where | Evidence |
|---|---|---|---|---|---|
| #20 | TMS-F-001 | TC-SCN-01 | Implemented (single intersection) | `simulation/scenario.py`, `tools/scenario_cli.py`, `data/scenarios.json` | `tests/test_scenario_creation.py` |
| #21 | TMS-F-004 | TC-VEH-02 | Implemented, red-light bug fixed | `simulation/traffic.py`, `simulation/engine.py` | `tests/test_vehicle_movement.py` |
| #22 | TMS-F-015 | TC-CTL-01 | Implemented | `simulation/engine.py`, `interface/dashboard.py` (wiring), `main.py` | `tests/test_engine_controls.py` |

Test command, from `Traffic_Management_System_MVP/` in a Python 3.12 venv:
`python -m pytest -q` → 63 passed (26 existing + 37 new).

## What was built

- **Scenario model (F-001).** A scenario has window and simulation settings plus a
  network: one `four_way` intersection and 1–4 approach roads (N/S/E/W), each with
  an id. `create_scenario()` and `python -m tools.scenario_cli create` build one,
  `save_scenario()` writes it (no silent overwrite), `load_scenario()` reads it, and
  `python main.py --scenario <file>` runs it. Only configured roads generate traffic,
  and each vehicle carries its `road_id`. Structural checks: required sections,
  approach in N/S/E/W, unique road ids and approaches, roads reference the
  intersection, exactly one intersection.
- **Simulation engine (F-015).** `SimulationEngine` owns the master clock and the
  RUNNING/PAUSED state. `tick` does nothing while paused; `step` advances one
  1/30 s tick only while paused; `reset` returns to time 0, no vehicles, zeroed
  metrics, NS_GREEN and the scenario's spawn interval, and keeps the pause state.
  Normal ticks and steps use the same order: signals first, then vehicles. Reset
  reseeds the RNG, so a reset run repeats the same arrivals. Controls emit events
  that the dashboard's event log shows.
- **Dashboard wiring.** SPACE, N, R, UP/DOWN and ESC now go through the engine. The
  status line shows RUNNING/PAUSED and simulated time. Drawing code is unchanged.

## Red-light bug (pre-existing; fixed as part of F-004)

- **Symptom:** vehicles crossed their stop line on red. Reproduced on `main` at
  `0a42c2d`: 3 crossings on red in the first 11.5 s of the default scenario.
- **Cause:** `TrafficSimulation._is_in_intersection` starts 8 px before the stop
  line (x=448 vs stop line x=456 for westbound traffic). Vehicles that stopped in
  that gap counted as "already in the intersection" and drove through on red.
- **Fix:** new `_has_passed_stop_line(car)` (`_distance_to_stop(car) < -0.01`), used
  in the two movement decisions in `update()`. `_is_in_intersection` is unchanged.
- **Regression test:** over 10 simulated minutes at spawn interval 0.25, no vehicle
  crosses its stop line unless its signal is GREEN. Both red-light tests fail
  against the old logic and pass with the fix.
- **Review:** this is in the TMS-F-005 (signal enforcement) area, so Aks
  (`WonderAks`) is asked to review.

## Deferred to Sprint 2 (not implemented here)

| Issue | SRS ID | Deferred work |
|---|---|---|
| #23 | TMS-F-017 | Save configuration and results (experiment store, save key) |
| #24 | TMS-F-019 | Range/type checks, collect all errors, refuse to start with a useful error |
| #25 | TMS-NF-003 | 5 × 30-minute headless reliability run |
| #26 | TMS-NF-007 | Reload saved experiments, configuration comparison |
| #27 | TMS-SR-003 | Sanitize imported data: size limit, NaN/Infinity, duplicate keys, unknown fields, name rules |

## Known limitations and notes

- One four-way intersection only; more are rejected with a clear message.
- In Sprint 1 an invalid scenario file stops with a Python error naming the problem;
  friendly error handling is TMS-F-019 (Sprint 2).
- On macOS, pygame 2.6.1 fonts fail on Python 3.14, so use a Python 3.12 venv for the window.
- `tests/test_startup.py` (TMS-NF-002) timed out once on the very first cold run in a
  new venv and passed on every rerun.
- Seen while wiring, not changed (outside this scope): in `interface/dashboard.py`
  `draw_panel`, a second panel rectangle is drawn at the left after the metrics text,
  covering it, and the event-log panel background is no longer drawn.
