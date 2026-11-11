import json

from simulation.engine import SimulationEngine
from simulation.report import build_summary_report, save_summary_report
from simulation.scenario import create_scenario


def make_engine(adaptive=False):
    scenario = create_scenario(
        "Report Test Scenario",
        adaptive_control=adaptive,
    )
    return SimulationEngine(scenario)


def test_report_contains_scenario_details():
    engine = make_engine()

    report = build_summary_report(engine)

    assert report["scenario"]["name"] == "Report Test Scenario"
    assert report["scenario"]["intersections"]
    assert report["scenario"]["roads"]


def test_report_identifies_fixed_time_strategy():
    engine = make_engine(adaptive=False)

    report = build_summary_report(engine)

    assert report["control_strategy"]["type"] == "Fixed-time"


def test_report_identifies_adaptive_strategy():
    engine = make_engine(adaptive=True)

    report = build_summary_report(engine)

    assert report["control_strategy"]["type"] == "Adaptive"


def test_report_contains_traffic_metrics():
    engine = make_engine()

    engine.metrics.spawned = 10
    engine.metrics.completed = 4
    engine.metrics.total_wait_seconds = 20
    engine.metrics.elapsed_seconds = 60

    report = build_summary_report(engine)
    metrics = report["traffic_metrics"]

    assert metrics["vehicles_spawned"] == 10
    assert metrics["vehicles_completed"] == 4
    assert metrics["throughput_per_minute"] == 4.0
    assert metrics["average_wait_seconds"] == 5.0


def test_report_includes_simulation_state():
    engine = make_engine()

    engine.tick(0.1)

    report = build_summary_report(engine)

    assert report["simulation"]["duration_seconds"] > 0
    assert report["simulation"]["ticks"] == 1


def test_report_is_saved_as_valid_json(tmp_path):
    engine = make_engine()

    output_path = save_summary_report(engine, tmp_path)

    assert output_path.exists()
    assert output_path.suffix == ".json"

    with output_path.open(encoding="utf-8") as file:
        report = json.load(file)

    assert report["scenario"]["name"] == "Report Test Scenario"
    assert "traffic_metrics" in report
    assert "control_strategy" in report