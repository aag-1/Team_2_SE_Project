# Sprint 2 implementation notes: validation, experiments and reliability

Owner: Aayush Gupta (PES2UG24CS018). Branch: `feature/aayush-sprint2-validation-experiments`,
based on `main` at `646fd9b`. Work date: 12 November 2026, after the official Sprint 2
window (26–30 Oct 2026); this is catch-up work, recorded with its real date.

This is a new supporting note. The submitted SRS, SAD and STP are unchanged.
Requirement IDs and test references follow the SRS.

## Sprint 2 status

| Issue | SRS ID | Test ref | Status | Where | Evidence |
|---|---|---|---|---|---|
| #23 | TMS-F-017 | TC-REP-01 | Implemented | `simulation/experiment_store.py`, key **S** in `interface/dashboard.py` | `tests/test_experiment_store.py` |
| #24 | TMS-F-019 | TC-SCN-02 | Implemented (console error) | `simulation/scenario.py`, `main.py`, `scenario_cli validate` | `tests/test_scenario_validation.py` |
| #25 | TMS-NF-003 | TC-NF-03 | Implemented (headless) | `tools/reliability_run.py` | `tests/test_reliability.py` |
| #26 | TMS-NF-007 | TC-NF-07 | Implemented | `compare_scenarios()`, `scenario_cli compare` | `tests/test_experiment_store.py` |
| #27 | TMS-SR-003 | TC-SEC-03 | Implemented | `read_json_file()` / `validate_scenario()` in `simulation/scenario.py` | `tests/test_input_security.py` |

Test command, from `Traffic_Management_System_MVP/` in a Python 3.12 venv:
`python -m pytest -q` → 149 passed (97 on `main` + 52 new).

Reliability command: `python -m tools.reliability_run --runs 5 --minutes 30`
→ `5/5 runs completed 30 simulated minutes without failure (100%)`, about 1.2 s per run.

## What was built

- **Validation (F-019).** `validate_scenario()` checks every field, collects all problems
  and raises one `ScenarioError` listing them. Numbers must be finite, the right type
  (no booleans, whole numbers where needed) and in range. It also checks teammates'
  options: `adaptive_control` (true/false), `phase_sequence` (known phases), min/max
  green (max ≥ min), emergency probability (0–1) and priority distance.
  `main.py` validates before the window opens; an invalid file prints
  "Simulation not started." with the list of problems and exits with code 2.
- **Sanitization (SR-003).** Files over 256 KB, non-UTF-8 text, NaN/Infinity, duplicate
  keys, deep nesting and unknown fields are rejected. Names, ids and titles must use
  safe characters; extra whitespace is collapsed. A 500-file random-corruption test
  checks that bad input is always rejected cleanly, never with a crash.
- **Experiments (F-017).** Key **S** saves `data/experiments/experiment_<time>.json`
  with the full configuration and the current results (`engine.snapshot()`). Files
  are written atomically (temp file + rename). `load_experiment()` re-validates
  everything, so a tampered file is rejected.
- **Reload (NF-007).** `python main.py --scenario <experiment file>` re-runs a saved
  configuration. `compare_scenarios()` and `scenario_cli compare` list any
  configuration differences; a save/reload round trip shows none, and re-running a
  reloaded experiment reproduces the saved results exactly.
- **Reliability (NF-003).** `tools/reliability_run.py` runs N consecutive headless runs
  of M simulated minutes, checking state invariants every simulated minute (vehicle
  counts match metrics, no negative waits, vehicles stay in the world).

## Sprint 1 audit (12 Nov 2026)

- PR #52 merged on 2 Nov; #20 closed by the merge, #21 and #22 closed on 3 Nov.
- Since then teammates extended `engine.py`, `traffic.py`, `signals.py` and
  `scenarios.json` (adaptive control, emergency priority, timestamps, reports).
  The red-light fix (`_has_passed_stop_line`) is still in place and its tests pass.
- The dashboard panel overlap noted in Sprint 1 has been fixed on `main`.

## Known limitations

- Validation errors are shown in the console, not in the pygame window.
- One four-way intersection only.
- New `simulation` settings must be added to `SIMULATION_LIMITS` (or
  `OTHER_SIMULATION_KEYS`) in `simulation/scenario.py`; otherwise scenario files using
  them are rejected as having unknown fields.
- The reliability run is headless; it does not exercise pygame drawing.
