"""TC-REP-01 (TMS-F-017) and TC-NF-07 (TMS-NF-007)."""
import json

import pytest

from simulation.engine import SimulationEngine
from simulation.experiment_store import (compare_scenarios, load_experiment,
                                         save_experiment)
from simulation.scenario import ScenarioError, create_scenario, load_scenario

DT = 1 / 30


def run(engine, seconds):
    for _ in range(round(seconds / DT)):
        engine.tick(DT)


def test_save_and_reload_without_data_loss(tmp_path, default_scenario):
    engine = SimulationEngine(default_scenario)
    run(engine, 90)
    results = engine.snapshot()
    path = save_experiment(tmp_path / "exp.json", default_scenario, results)
    loaded = load_experiment(path)
    assert loaded.results == results                    # TC-REP-01
    assert compare_scenarios(default_scenario, loaded.scenario) == []  # TC-NF-07
    assert loaded.scenario == default_scenario
    assert not list(tmp_path.glob(".tmp_*"))           # atomic write left no temp file


def test_non_default_configuration_round_trips_exactly(tmp_path):
    scenario = create_scenario("Odd values", approaches=["W", "S"], intersection_id="X_9",
                               spawn_interval_seconds=0.7300000000000001, vehicle_speed=99.125,
                               green_seconds=7, amber_seconds=2.5, red_clearance_seconds=0,
                               seed=123456)
    path = save_experiment(tmp_path / "e.json", scenario, {"note": "x", "value": 0.1 + 0.2})
    loaded = load_experiment(path)
    assert compare_scenarios(scenario, loaded.scenario) == []
    assert loaded.results["value"] == 0.1 + 0.2


def test_compare_reports_unintended_changes(default_scenario):
    other = create_scenario(default_scenario.name, approaches=["N", "S", "E"],
                            green_seconds=20)
    diffs = compare_scenarios(default_scenario, other)
    assert any("green_seconds" in d for d in diffs)
    assert any("roads[3]" in d for d in diffs)


def test_reloaded_experiment_reproduces_same_results(tmp_path, default_scenario):
    engine = SimulationEngine(default_scenario)
    run(engine, 120)
    path = save_experiment(tmp_path / "exp.json", default_scenario, engine.snapshot())
    loaded = load_experiment(path)
    rerun = SimulationEngine(loaded.scenario)
    run(rerun, 120)
    assert rerun.snapshot() == loaded.results


def test_experiment_file_usable_as_scenario(tmp_path, default_scenario):
    path = save_experiment(tmp_path / "exp.json", default_scenario, {"a": 1})
    assert load_scenario(path) == default_scenario      # python main.py --scenario exp.json


def test_tampered_experiment_rejected(tmp_path, default_scenario):
    path = save_experiment(tmp_path / "exp.json", default_scenario, {"a": 1})
    doc = json.loads(path.read_text())
    doc["scenario"]["simulation"]["vehicle_speed"] = -40
    path.write_text(json.dumps(doc))
    with pytest.raises(ScenarioError, match="vehicle_speed"):
        load_experiment(path)


@pytest.mark.parametrize("results", [{"x": float("nan")}, {"x": [1, 2]}, ["not", "dict"]])
def test_invalid_results_not_saved(tmp_path, default_scenario, results):
    with pytest.raises(ScenarioError):
        save_experiment(tmp_path / "e.json", default_scenario, results)
    assert not (tmp_path / "e.json").exists()


def test_cli_compare_shows_no_unintended_changes(tmp_path, capsys, default_scenario):
    """TC-NF-07 from the command line: saved experiment vs its source configuration."""
    from tools import scenario_cli
    exp = save_experiment(tmp_path / "exp.json", default_scenario, {"a": 1})
    source = tmp_path / "source.json"
    source.write_text(json.dumps(default_scenario.to_dict()))
    assert scenario_cli.main(["compare", str(source), str(exp)]) == 0
    assert "IDENTICAL" in capsys.readouterr().out
    changed = create_scenario(default_scenario.name, green_seconds=20)
    other = save_experiment(tmp_path / "other.json", changed, {"a": 1})
    assert scenario_cli.main(["compare", str(exp), str(other)]) == 1
    assert "green_seconds" in capsys.readouterr().out
