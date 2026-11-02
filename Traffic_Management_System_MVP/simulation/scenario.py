"""Scenario Manager: configurable roads and intersections (TMS-F-001).

A scenario is the window + simulation settings plus a road network. This
module only checks the network's *structure* (required fields, N/S/E/W
approaches, unique roads, road -> intersection references). Range checks,
collected error lists and file sanitization are TMS-F-019 / TMS-SR-003
(Sprint 2) and are deliberately not here yet.

MVP boundary: the renderer and traffic model support ONE four-way
intersection with up to four straight-through approach roads. Networks with
more intersections are rejected with an explicit message.
"""
from __future__ import annotations

import copy
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1
APPROACHES = ("N", "S", "E", "W")

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
    """Raised when a scenario's structure is invalid."""


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


def validate_structure(raw: Any) -> Scenario:
    """Build a Scenario from raw data, raising ScenarioError on the first structural problem."""
    if not isinstance(raw, dict):
        raise ScenarioError("Scenario must be a JSON object")
    for key in ("window", "simulation"):
        if not isinstance(raw.get(key), dict):
            raise ScenarioError(f"Scenario is missing the '{key}' section")

    network = raw.get("network", DEFAULT_NETWORK)  # older files: default 4-road network
    if not isinstance(network, dict):
        raise ScenarioError("'network' must be an object")

    raw_ints = network.get("intersections")
    if not isinstance(raw_ints, list) or not raw_ints:
        raise ScenarioError("network.intersections must be a non-empty list")
    if len(raw_ints) > 1:
        raise ScenarioError(f"This version supports exactly one intersection (got {len(raw_ints)}); "
                            "multi-intersection networks are not implemented")
    item = raw_ints[0]
    if not isinstance(item, dict) or not item.get("id"):
        raise ScenarioError("network.intersections[0] needs an 'id'")
    if item.get("type", "four_way") != "four_way":
        raise ScenarioError("network.intersections[0].type must be 'four_way'")
    intersection = Intersection(str(item["id"]))

    raw_roads = network.get("roads")
    if not isinstance(raw_roads, list) or not raw_roads:
        raise ScenarioError("network.roads must be a non-empty list")
    roads, seen_ids, seen_approaches = [], set(), set()
    for idx, road in enumerate(raw_roads):
        label = f"network.roads[{idx}]"
        if not isinstance(road, dict) or not all(road.get(k) for k in ("id", "intersection", "approach")):
            raise ScenarioError(f"{label} needs 'id', 'intersection' and 'approach'")
        if road["approach"] not in APPROACHES:
            raise ScenarioError(f"{label}.approach must be one of {', '.join(APPROACHES)}")
        if road["intersection"] != intersection.id:
            raise ScenarioError(f"{label}.intersection '{road['intersection']}' "
                                "does not match a defined intersection")
        if road["id"] in seen_ids:
            raise ScenarioError(f"{label}.id '{road['id']}' is used more than once")
        if road["approach"] in seen_approaches:
            raise ScenarioError(f"{label}.approach '{road['approach']}' is used by more than one road")
        seen_ids.add(road["id"])
        seen_approaches.add(road["approach"])
        roads.append(Road(str(road["id"]), intersection.id, road["approach"]))

    return Scenario(name=str(raw.get("name", DEFAULT_SCENARIO["name"])),
                    window=copy.deepcopy(raw["window"]),
                    simulation=copy.deepcopy(raw["simulation"]),
                    intersections=(intersection,), roads=tuple(roads))


def create_scenario(name: str, approaches=APPROACHES, intersection_id: str = "INT-1",
                    **simulation_overrides: Any) -> Scenario:
    """Build a scenario from defaults plus operator-chosen roads, intersection and settings."""
    data = copy.deepcopy(DEFAULT_SCENARIO)
    data["name"] = name
    data["simulation"].update(simulation_overrides)
    data["network"] = {
        "intersections": [{"id": intersection_id, "type": "four_way"}],
        "roads": [{"id": f"R-{a}", "intersection": intersection_id, "approach": a}
                  for a in approaches],
    }
    return validate_structure(data)


def load_scenario(path: str | Path) -> Scenario:
    with Path(path).open("r", encoding="utf-8") as handle:
        return validate_structure(json.load(handle))


def save_scenario(path: str | Path, scenario: Scenario, overwrite: bool = False) -> Path:
    path = Path(path)
    if path.exists() and not overwrite:
        raise FileExistsError(f"'{path}' already exists")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(scenario.to_dict(), indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8")
    return path
