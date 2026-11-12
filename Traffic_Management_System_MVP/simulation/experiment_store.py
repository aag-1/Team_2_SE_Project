"""Experiment storage: save configuration + results and reload them.

Requirements covered:
  TMS-F-017  save simulation configuration and experiment results

Loading re-uses the scenario validation layer (TMS-SR-003), so a tampered or
corrupted experiment file is rejected with a clear message instead of crashing.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from simulation.scenario import (Scenario, ScenarioError, atomic_write_json, read_json_file,
                                 validate_scenario)

EXPERIMENT_FORMAT = "tms-experiment/1"
MAX_RESULT_FIELDS = 64


@dataclass(frozen=True)
class Experiment:
    scenario: Scenario
    results: dict[str, Any]
    saved_at: str


def _validate_results(results: Any) -> dict[str, Any]:
    if not isinstance(results, dict):
        raise ScenarioError("results must be an object")
    errors = []
    if len(results) > MAX_RESULT_FIELDS:
        errors.append(f"results may contain at most {MAX_RESULT_FIELDS} fields")
    for key, value in results.items():
        if not isinstance(key, str) or not key or len(key) > 64:
            errors.append(f"results key {key!r} is invalid")
        elif isinstance(value, float) and not math.isfinite(value):
            errors.append(f"results.{key} must be finite")
        elif isinstance(value, bool) or not isinstance(value, (int, float, str)) \
                or (isinstance(value, str) and len(value) > 200):
            errors.append(f"results.{key} must be a number or short text")
    if errors:
        raise ScenarioError(errors)
    return dict(results)


def save_experiment(path: str | Path, scenario: Scenario, results: dict[str, Any],
                    saved_at: datetime | None = None) -> Path:
    if not isinstance(scenario, Scenario):
        raise TypeError("save_experiment requires a validated Scenario")
    stamp = (saved_at or datetime.now(timezone.utc)).isoformat(timespec="seconds")
    document = {
        "format": EXPERIMENT_FORMAT,
        "saved_at": stamp,
        "scenario": scenario.to_dict(),
        "results": _validate_results(results),
    }
    atomic_write_json(path, document)
    return Path(path)


def load_experiment(path: str | Path) -> Experiment:
    data = read_json_file(path)
    if not isinstance(data, dict):
        raise ScenarioError("Experiment file must be a JSON object")
    unknown = sorted(map(str, set(data) - {"format", "saved_at", "scenario", "results"}))
    if unknown:
        raise ScenarioError(f"Experiment file has unknown field(s): {', '.join(unknown)}")
    if data.get("format") != EXPERIMENT_FORMAT:
        raise ScenarioError(
            f"Unsupported experiment format {data.get('format')!r} (expected {EXPERIMENT_FORMAT})")
    saved_at = data.get("saved_at")
    try:
        datetime.fromisoformat(saved_at)
    except (TypeError, ValueError):
        raise ScenarioError("saved_at must be an ISO-8601 timestamp") from None
    scenario = validate_scenario(data.get("scenario"))
    results = _validate_results(data.get("results"))
    return Experiment(scenario=scenario, results=results, saved_at=saved_at)

