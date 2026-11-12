"""TC-SCN-02 (TMS-F-019): invalid configuration prevents execution and shows a useful error."""
import pytest

import main
from simulation.scenario import ScenarioError, validate_scenario
from tools import scenario_cli


@pytest.mark.parametrize("section,key,value,expected", [
    ("simulation", "spawn_interval_seconds", 0, "spawn_interval_seconds must be between"),
    ("simulation", "green_seconds", -5, "green_seconds must be between"),
    ("simulation", "vehicle_speed", "fast", "vehicle_speed must be a number"),
    ("simulation", "tick_rate", True, "tick_rate must be a number"),
    ("simulation", "tick_rate", 30.5, "tick_rate must be a whole number"),
    ("simulation", "emergency_spawn_probability", 1.5, "emergency_spawn_probability must be between"),
    ("simulation", "adaptive_control", "yes", "adaptive_control must be true or false"),
    ("simulation", "phase_sequence", ["NS_GREEN", "PURPLE"], "phase_sequence must be a list"),
    ("simulation", "phase_sequence", [], "phase_sequence must be a list"),
    ("window", "width", 100, "window.width must be between"),
])
def test_out_of_range_values_are_named_in_error(raw_default, section, key, value, expected):
    raw_default[section][key] = value
    with pytest.raises(ScenarioError) as exc:
        validate_scenario(raw_default)
    assert any(expected in e for e in exc.value.errors), exc.value.errors


def test_all_errors_reported_together(raw_default):
    raw_default["simulation"]["vehicle_speed"] = 0
    raw_default["simulation"]["amber_seconds"] = 99
    del raw_default["simulation"]["vehicle_gap"]
    with pytest.raises(ScenarioError) as exc:
        validate_scenario(raw_default)
    assert len(exc.value.errors) == 3


def test_min_green_above_max_green_rejected(raw_default):
    raw_default["simulation"].update(min_green_seconds=40, max_green_seconds=20)
    with pytest.raises(ScenarioError, match="max_green_seconds must be at least"):
        validate_scenario(raw_default)


def test_teammate_signal_options_are_accepted_and_kept(raw_default):
    raw_default["simulation"].update(adaptive_control=True, min_green_seconds=6,
                                     max_green_seconds=30, emergency_spawn_probability=0.0,
                                     emergency_priority_distance=210,
                                     phase_sequence=["NS_GREEN", "EW_GREEN"])
    sim = validate_scenario(raw_default).simulation
    assert sim["adaptive_control"] is True
    assert sim["phase_sequence"] == ["NS_GREEN", "EW_GREEN"]
    assert sim["emergency_priority_distance"] == 210


def test_main_does_not_start_simulation_on_invalid_file(tmp_path, monkeypatch, capsys):
    bad = tmp_path / "bad.json"
    bad.write_text('{"window": {"width": 1100, "height": 760}, '
                   '"simulation": {"spawn_interval_seconds": -1}}')
    import interface.dashboard as dashboard
    monkeypatch.setattr(dashboard, "run_app",
                        lambda *a, **k: pytest.fail("simulation must not start"))
    assert main.main(["--scenario", str(bad)]) == 2
    err = capsys.readouterr().err
    assert "Simulation not started" in err and "spawn_interval_seconds" in err


def test_main_starts_with_valid_default(monkeypatch):
    import interface.dashboard as dashboard
    started = []
    monkeypatch.setattr(dashboard, "run_app", started.append)
    assert main.main([]) == 0
    assert started[0].name == "Default four-way intersection"


def test_cli_validate_reports_valid_and_invalid(tmp_path, capsys):
    good, bad = tmp_path / "good.json", tmp_path / "bad.json"
    assert scenario_cli.main(["create", "--name", "Good", "--out", str(good)]) == 0
    assert scenario_cli.main(["validate", str(good)]) == 0
    assert "VALID" in capsys.readouterr().out
    bad.write_text('{"window": {}, "simulation": {}}')
    assert scenario_cli.main(["validate", str(bad)]) == 1
    assert "missing required field" in capsys.readouterr().err
