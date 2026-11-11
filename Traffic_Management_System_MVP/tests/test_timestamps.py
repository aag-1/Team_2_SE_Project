
from datetime import datetime

from simulation.engine import SimulationEngine
from simulation.scenario import create_scenario


def make_engine():
    return SimulationEngine(
        create_scenario("Timestamp Test Scenario")
    )


def test_emitted_event_contains_iso_timestamp():
    engine = make_engine()
    captured = []

    engine.add_listener(
        lambda event_type, message, context:
        captured.append((event_type, message, context))
    )

    engine.pause()

    assert captured
    timestamp = captured[0][2]["timestamp"]

    parsed = datetime.fromisoformat(timestamp)
    assert parsed.tzinfo is not None


def test_event_contains_simulation_time_and_timestamp():
    engine = make_engine()
    captured = []

    engine.add_listener(
        lambda event_type, message, context:
        captured.append(context)
    )

    engine.pause()

    assert "sim_time" in captured[0]
    assert "timestamp" in captured[0]


def test_each_event_gets_a_timestamp():
    engine = make_engine()
    captured = []

    engine.add_listener(
        lambda event_type, message, context:
        captured.append(context["timestamp"])
    )

    engine.pause()
    engine.resume()

    assert len(captured) == 2
    assert all(timestamp for timestamp in captured)


def test_timestamp_is_timezone_aware():
    engine = make_engine()
    captured = []

    engine.add_listener(
        lambda event_type, message, context:
        captured.append(context["timestamp"])
    )

    engine.pause()

    timestamp = datetime.fromisoformat(captured[0])
    assert timestamp.utcoffset() is not None
