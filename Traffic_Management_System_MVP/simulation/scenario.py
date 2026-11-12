"""Scenario Manager and validation layer.

Requirements covered:
  TMS-F-001  create configurable traffic scenarios (roads + intersections)
  TMS-F-019  validate scenario parameters before a simulation starts
  TMS-SR-003 validate and sanitize imported scenario/configuration data

Every scenario that reaches the Simulation Engine comes through
``validate_scenario`` (or a loader that calls it). Invalid input raises
``ScenarioError`` listing every problem found; it never crashes the
application with an unrelated exception.

MVP boundary: the renderer and traffic model support ONE four-way
intersection with up to four straight-through approach roads (N, S, E, W).
Networks with more intersections are rejected with an explicit message.
"""
from __future__ import annotations

import copy
import json
import math
import os
import re
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1
MAX_FILE_BYTES = 256 * 1024
APPROACHES = ("N", "S", "E", "W")
PHASES = ("NS_GREEN", "NS_AMBER", "ALL_RED_TO_EW", "EW_GREEN", "EW_AMBER", "ALL_RED_TO_NS")

_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,32}$")
_NAME_RE = re.compile(r"^[A-Za-z0-9 _.,()'-]{1,60}$")

# key: (type, minimum, maximum, required)
SIMULATION_LIMITS: dict[str, tuple[type, float, float, bool]] = {
    "tick_rate": (int, 10, 240, True),
    "spawn_interval_seconds": (float, 0.25, 10.0, True),
    "vehicle_speed": (float, 10.0, 500.0, True),
    "vehicle_length": (float, 10.0, 80.0, True),
    "vehicle_gap": (float, 2.0, 80.0, True),
    "green_seconds": (float, 1.0, 300.0, True),
    "amber_seconds": (float, 1.0, 30.0, True),
    "red_clearance_seconds": (float, 0.0, 30.0, True),
    "seed": (int, 0, 2**31 - 1, False),
    "min_green_seconds": (float, 1.0, 300.0, False),
    "max_green_seconds": (float, 1.0, 600.0, False),
    "emergency_spawn_probability": (float, 0.0, 1.0, False),
    "emergency_priority_distance": (float, 1.0, 2000.0, False),
}
OTHER_SIMULATION_KEYS = {"phase_sequence", "adaptive_control"}
WINDOW_LIMITS: dict[str, tuple[type, float, float, bool]] = {
    "width": (int, 800, 3840, True),
    "height": (int, 600, 2160, True),
}

DEFAULT_NETWORK = {
    "intersections": [{"id": "INT-1", "type": "four_way"}],
    "roads": [{"id": f"R-{a}", "intersection": "INT-1", "approach": a} for a in APPROACHES],
}
DEFAULT_SCENARIO: dict[str, Any] = {
    "schema_version": SCHEMA_VERSION,
    "name": "Default four-way intersection",
    "window": {"width": 1100, "height": 760,
               "title": "Traffic Management System — Simulation"},
    "simulation": {
        "tick_rate": 60, "spawn_interval_seconds": 1.25, "vehicle_speed": 145,
        "vehicle_length": 30, "vehicle_gap": 13, "green_seconds": 12,
        "amber_seconds": 3, "red_clearance_seconds": 1, "seed": 7,
    },
    "network": DEFAULT_NETWORK,
}


class ScenarioError(ValueError):
    """Raised when scenario data is malformed, unsafe or out of range."""

    def __init__(self, errors: list[str] | str):
        self.errors = [errors] if isinstance(errors, str) else (list(errors) or ["Unknown error"])
        super().__init__("Invalid scenario:\n  - " + "\n  - ".join(self.errors))


@dataclass(frozen=True)
class Road:
    id: str
    intersection: str
    approach: str


@dataclass(frozen=True)
class Intersection:
    id: str
    type: str = "four_way"


@dataclass(frozen=True)
class Scenario:
    """A validated scenario. Build it only via validate_scenario() or the loaders."""
    name: str
    window: dict = field(hash=False)
    simulation: dict = field(hash=False)
    intersections: tuple[Intersection, ...]
    roads: tuple[Road, ...]

    @property
    def approaches(self) -> tuple[str, ...]:
        return tuple(road.approach for road in self.roads)

    @property
    def road_ids(self) -> dict[str, str]:
        return {road.approach: road.id for road in self.roads}

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "name": self.name,
            "window": copy.deepcopy(self.window),
            "simulation": copy.deepcopy(self.simulation),
            "network": {
                "intersections": [{"id": i.id, "type": i.type} for i in self.intersections],
                "roads": [{"id": r.id, "intersection": r.intersection, "approach": r.approach}
                          for r in self.roads],
            },
        }


# ------------------------------------------------------------- reading (SR-003)

def _reject_constant(value: str):
    raise ValueError(f"non-finite number '{value}' is not allowed")


def _no_duplicate_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate key '{key}'")
        result[key] = value
    return result


def parse_json_text(text: str) -> Any:
    """Strict JSON parse: no NaN/Infinity, no duplicate keys."""
    try:
        return json.loads(text, parse_constant=_reject_constant,
                          object_pairs_hook=_no_duplicate_keys)
    except RecursionError:
        raise ScenarioError("File is nested too deeply") from None
    except json.JSONDecodeError as exc:
        raise ScenarioError(
            f"File is not valid JSON (line {exc.lineno}, column {exc.colno}): {exc.msg}") from None
    except ValueError as exc:
        raise ScenarioError(f"File is not valid JSON: {exc}") from None


def read_json_file(path: str | Path) -> Any:
    """Read a JSON file safely: size limit, UTF-8 only, strict parsing."""
    path = Path(path)
    try:
        if not path.is_file():
            raise ScenarioError(f"'{path}' does not exist or is not a file")
        size = path.stat().st_size
        if size > MAX_FILE_BYTES:
            raise ScenarioError(f"'{path.name}' is {size} bytes; the limit is {MAX_FILE_BYTES} bytes")
        text = path.read_bytes().decode("utf-8-sig")
    except UnicodeDecodeError:
        raise ScenarioError(f"'{path.name}' is not UTF-8 text") from None
    except OSError as exc:
        raise ScenarioError(f"Cannot read '{path}': {exc.strerror or exc}") from None
    return parse_json_text(text)


def load_scenario(path: str | Path) -> Scenario:
    """Load and validate a scenario file, or the scenario inside a saved experiment."""
    data = read_json_file(path)
    if isinstance(data, dict) and "format" in data and "scenario" in data:
        data = data["scenario"]  # saved experiment file (see experiment_store)
    return validate_scenario(data)


# ------------------------------------------------------- validation (F-019)

def _clean_text(value: Any, label: str, pattern: re.Pattern, errors: list[str],
                hint: str) -> str | None:
    if not isinstance(value, str):
        errors.append(f"{label} must be text")
        return None
    cleaned = " ".join(value.split())  # trim and collapse whitespace
    if not pattern.fullmatch(cleaned):
        errors.append(f"{label} '{value[:40]}' is invalid: {hint}")
        return None
    return cleaned


def _number(value: Any, label: str, kind: type, low: float, high: float, errors: list[str]):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        errors.append(f"{label} must be a number, got {type(value).__name__}")
        return None
    if isinstance(value, float) and not math.isfinite(value):
        errors.append(f"{label} must be a finite number")
        return None
    if kind is int and isinstance(value, float):
        if not value.is_integer():
            errors.append(f"{label} must be a whole number, got {value}")
            return None
        value = int(value)
    if not low <= value <= high:
        errors.append(f"{label} must be between {low:g} and {high:g}, got {value:g}")
        return None
    return value


def _check_keys(section: dict, allowed: set[str], required: set[str], label: str,
                errors: list[str]) -> None:
    unknown = sorted(map(str, set(section) - allowed))
    if unknown:
        errors.append(f"{label} has unknown field(s): {', '.join(unknown)}")
    missing = sorted(required - set(section))
    if missing:
        errors.append(f"{label} is missing required field(s): {', '.join(missing)}")


def _numbers(raw: dict, limits: dict, label: str, extra: set[str], errors: list[str]) -> dict:
    _check_keys(raw, set(limits) | extra, {k for k, v in limits.items() if v[3]}, label, errors)
    return {key: _number(raw[key], f"{label}.{key}", kind, low, high, errors)
            for key, (kind, low, high, _) in limits.items() if key in raw}


def _section(raw: dict, key: str, errors: list[str]) -> dict | None:
    value = raw.get(key)
    if not isinstance(value, dict):
        errors.append(f"'{key}' must be an object" if key in raw
                      else f"Scenario is missing the '{key}' section")
        return None
    return value


def validate_scenario(raw: Any) -> Scenario:
    """Validate untrusted scenario data and return a sanitized Scenario."""
    if not isinstance(raw, dict):
        raise ScenarioError("Scenario must be a JSON object")
    errors: list[str] = []
    _check_keys(raw, {"schema_version", "name", "window", "simulation", "network"},
                set(), "Scenario", errors)

    version = raw.get("schema_version", SCHEMA_VERSION)
    if isinstance(version, bool) or version != SCHEMA_VERSION:
        errors.append(f"schema_version {version!r} is not supported (expected {SCHEMA_VERSION})")

    name = _clean_text(raw.get("name", DEFAULT_SCENARIO["name"]), "name", _NAME_RE, errors,
                       "use 1-60 letters, digits, spaces or . , ( ) ' - _")

    window_raw = _section(raw, "window", errors)
    window = {}
    if window_raw is not None:
        window = _numbers(window_raw, WINDOW_LIMITS, "window", {"title"}, errors)
        title = window_raw.get("title", DEFAULT_SCENARIO["window"]["title"])
        if not isinstance(title, str) or not title.strip() or len(title) > 100 \
                or not title.isprintable():
            errors.append("window.title must be 1-100 printable characters")
        else:
            window["title"] = " ".join(title.split())

    sim_raw = _section(raw, "simulation", errors)
    simulation = {}
    if sim_raw is not None:
        simulation = _numbers(sim_raw, SIMULATION_LIMITS, "simulation", OTHER_SIMULATION_KEYS,
                              errors)
        _validate_signal_options(sim_raw, simulation, errors)

    intersections, roads = _validate_network(raw.get("network", DEFAULT_NETWORK), errors)

    if window.get("width") and window.get("height") and simulation.get("vehicle_length"):
        if simulation["vehicle_length"] * 6 > min(window["width"], window["height"]) / 2:
            errors.append("simulation.vehicle_length is too large for the window size")

    if errors:
        raise ScenarioError(errors)
    return Scenario(name=name, window=window, simulation=simulation,
                    intersections=tuple(intersections), roads=tuple(roads))


def _validate_signal_options(sim_raw: dict, simulation: dict, errors: list[str]) -> None:
    if "adaptive_control" in sim_raw:
        if isinstance(sim_raw["adaptive_control"], bool):
            simulation["adaptive_control"] = sim_raw["adaptive_control"]
        else:
            errors.append("simulation.adaptive_control must be true or false")
    if "phase_sequence" in sim_raw:
        seq = sim_raw["phase_sequence"]
        if not isinstance(seq, list) or not 1 <= len(seq) <= 12 \
                or any(not isinstance(p, str) or p not in PHASES for p in seq):
            errors.append(f"simulation.phase_sequence must be a list of 1-12 phases from "
                          f"{', '.join(PHASES)}")
        else:
            simulation["phase_sequence"] = list(seq)
    low, high = simulation.get("min_green_seconds"), simulation.get("max_green_seconds")
    if low is not None and high is not None and high < low:
        errors.append("simulation.max_green_seconds must be at least min_green_seconds")


def _validate_network(net_raw: Any, errors: list[str]):
    intersections: list[Intersection] = []
    roads: list[Road] = []
    if not isinstance(net_raw, dict):
        errors.append("'network' must be an object")
        return intersections, roads
    _check_keys(net_raw, {"intersections", "roads"}, {"intersections", "roads"}, "network", errors)

    raw_ints = net_raw.get("intersections")
    if not isinstance(raw_ints, list) or not raw_ints:
        errors.append("network.intersections must be a non-empty list")
        raw_ints = []
    elif len(raw_ints) > 1:
        errors.append("This version supports exactly one intersection "
                      f"(got {len(raw_ints)}); multi-intersection networks are not implemented")
    for idx, item in enumerate(raw_ints[:1]):
        label = f"network.intersections[{idx}]"
        if not isinstance(item, dict):
            errors.append(f"{label} must be an object")
            continue
        _check_keys(item, {"id", "type"}, {"id"}, label, errors)
        iid = _clean_text(item.get("id"), f"{label}.id", _ID_RE, errors,
                          "use 1-32 letters, digits, '-' or '_'")
        if item.get("type", "four_way") != "four_way":
            errors.append(f"{label}.type must be 'four_way'")
        elif iid:
            intersections.append(Intersection(iid))

    raw_roads = net_raw.get("roads")
    if not isinstance(raw_roads, list) or not raw_roads:
        errors.append("network.roads must be a non-empty list")
        raw_roads = []
    elif len(raw_roads) > len(APPROACHES):
        errors.append(f"network.roads may contain at most {len(APPROACHES)} roads")
        raw_roads = raw_roads[:len(APPROACHES)]
    known_ints = {i.id for i in intersections}
    seen_ids, seen_approaches = set(), set()
    for idx, item in enumerate(raw_roads):
        label = f"network.roads[{idx}]"
        if not isinstance(item, dict):
            errors.append(f"{label} must be an object")
            continue
        _check_keys(item, {"id", "intersection", "approach"},
                    {"id", "intersection", "approach"}, label, errors)
        rid = _clean_text(item.get("id"), f"{label}.id", _ID_RE, errors,
                          "use 1-32 letters, digits, '-' or '_'") if "id" in item else None
        approach = item.get("approach")
        if "approach" in item and approach not in APPROACHES:
            errors.append(f"{label}.approach must be one of {', '.join(APPROACHES)}")
            approach = None
        target = item.get("intersection")
        if known_ints and "intersection" in item and target not in known_ints:
            errors.append(f"{label}.intersection '{target}' does not match a defined intersection")
            target = None
        if rid and rid in seen_ids:
            errors.append(f"{label}.id '{rid}' is used more than once")
        if approach and approach in seen_approaches:
            errors.append(f"{label}.approach '{approach}' is used by more than one road")
        if rid and approach and target:
            seen_ids.add(rid)
            seen_approaches.add(approach)
            roads.append(Road(rid, target, approach))
    return intersections, roads


# --------------------------------------------------------------- writing

def atomic_write_json(path: str | Path, data: Any) -> None:
    """Write JSON via a temp file + rename so a crash never leaves a half-written file."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".tmp_", suffix=".json", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2, allow_nan=False, ensure_ascii=False)
            handle.write("\n")
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise


# --------------------------------------------------------------- creation (F-001)

def create_scenario(name: str, approaches=APPROACHES, intersection_id: str = "INT-1",
                    **simulation_overrides: Any) -> Scenario:
    """Build a validated scenario from defaults plus operator-chosen roads and settings."""
    data = copy.deepcopy(DEFAULT_SCENARIO)
    data["name"] = name
    data["simulation"].update(simulation_overrides)
    data["network"] = {
        "intersections": [{"id": intersection_id, "type": "four_way"}],
        "roads": [{"id": f"R-{a}", "intersection": intersection_id, "approach": a}
                  for a in approaches],
    }
    return validate_scenario(data)


def save_scenario(path: str | Path, scenario: Scenario, overwrite: bool = False) -> Path:
    """Write a validated scenario to disk as JSON (never silently overwrites)."""
    path = Path(path)
    if path.exists() and not overwrite:
        raise FileExistsError(f"'{path}' already exists")
    atomic_write_json(path, scenario.to_dict())
    return path
