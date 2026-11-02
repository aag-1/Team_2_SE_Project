"""TC-SCN-01 (TMS-F-001): scenario created with valid parameters."""
import json

import pytest

from simulation.engine import SimulationEngine
from simulation.scenario import (Scenario, ScenarioError, create_scenario, load_scenario,
                                 validate_structure)
from tools import scenario_cli


def test_default_scenario_file_loads(default_scenario):
    assert isinstance(default_scenario, Scenario)
    assert default_scenario.approaches == ("N", "S", "E", "W")
    assert default_scenario.intersections[0].id == "INT-1"
    assert default_scenario.road_ids == {"N": "R-N", "S": "R-S", "E": "R-E", "W": "R-W"}


def test_operator_can_configure_roads_and_intersection():
    sc = create_scenario("T junction", approaches=["N", "S", "E"], intersection_id="JCT-7",
                         spawn_interval_seconds=0.8, green_seconds=20)
    assert sc.approaches == ("N", "S", "E")
    assert {r.intersection for r in sc.roads} == {"JCT-7"}
    engine = SimulationEngine(sc)
    assert engine.traffic.approaches == ("N", "S", "E")
    assert engine.traffic.spawn_interval == 0.8
    assert engine.signals.green_seconds == 20


def test_scenario_round_trips_through_to_dict(raw_default):
    sc = validate_structure(raw_default)
    assert validate_structure(sc.to_dict()) == sc


def test_file_without_network_gets_default_roads(raw_default):
    del raw_default["network"]
    assert validate_structure(raw_default).approaches == ("N", "S", "E", "W")


def test_cli_create_writes_loadable_file(tmp_path, capsys):
    out = tmp_path / "rush.json"
    code = scenario_cli.main(["create", "--name", "Rush hour", "--approaches", "N,E",
                              "--spawn-interval", "0.6", "--out", str(out)])
    assert code == 0 and "Created" in capsys.readouterr().out
    loaded = load_scenario(out)
    assert loaded.approaches == ("N", "E")
    assert loaded.simulation["spawn_interval_seconds"] == 0.6
    # refuses to overwrite silently
    assert scenario_cli.main(["create", "--name", "x", "--out", str(out)]) == 1
    assert load_scenario(out).name == "Rush hour"


def test_cli_rejects_bad_approach(tmp_path):
    out = tmp_path / "bad.json"
    assert scenario_cli.main(["create", "--name", "x", "--approaches", "N,Q",
                              "--out", str(out)]) == 1
    assert not out.exists()


@pytest.mark.parametrize("mutate,expected", [
    (lambda d: d["network"]["roads"][1].update(approach="N"), "used by more than one road"),
    (lambda d: d["network"]["roads"][1].update(id="R-N"), "used more than once"),
    (lambda d: d["network"]["roads"][2].update(intersection="INT-99"),
     "does not match a defined intersection"),
    (lambda d: d["network"]["roads"][3].update(approach="NE"), "approach must be one of"),
    (lambda d: d["network"]["roads"][0].pop("id"), "needs 'id'"),
    (lambda d: d["network"]["intersections"].append({"id": "INT-2"}), "exactly one intersection"),
    (lambda d: d["network"].update(roads=[]), "non-empty list"),
    (lambda d: d.pop("simulation"), "missing the 'simulation' section"),
])
def test_structural_problems_are_rejected(raw_default, mutate, expected):
    mutate(raw_default)
    with pytest.raises(ScenarioError, match=expected):
        validate_structure(raw_default)


def test_engine_refuses_raw_dict(raw_default):
    with pytest.raises(TypeError):
        SimulationEngine(raw_default)


def test_saved_file_is_plain_json(tmp_path):
    out = tmp_path / "s.json"
    scenario_cli.main(["create", "--name", "Plain", "--out", str(out)])
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["network"]["intersections"] == [{"id": "INT-1", "type": "four_way"}]
