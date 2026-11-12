"""TC-REP-01 (TMS-F-017): saved file/result can be reloaded without data loss."""
import json

import pytest

from simulation.engine import SimulationEngine
from simulation.experiment_store import load_experiment, save_experiment
from simulation.scenario import ScenarioError, load_scenario

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
    assert loaded.scenario == default_scenario
    assert not list(tmp_path.glob(".tmp_*"))           # atomic write left no temp file


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
