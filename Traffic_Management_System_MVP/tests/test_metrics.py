from simulation.metrics import Metrics


def test_metrics_calculations():
    metrics = Metrics(spawned=10, completed=4, total_wait_seconds=20, elapsed_seconds=120)
    assert metrics.active_count == 6
    assert metrics.throughput_per_minute == 2
    assert metrics.average_wait_seconds == 5


def test_zero_elapsed_and_no_completed_are_safe():
    metrics = Metrics()
    assert metrics.throughput_per_minute == 0
    assert metrics.average_wait_seconds == 0

from simulation.traffic import TrafficSimulation, Vehicle


class MockSignals:
    def state_for(self, direction):
        return "RED"


def create_simulation():
    metrics = Metrics()

    return TrafficSimulation(
        width=800,
        height=600,
        signals=MockSignals(),
        metrics=metrics,
    )


def test_traffic_density_empty_roads():
    sim = create_simulation()

    density = sim.traffic_density()

    assert density == {
        "N": 0,
        "S": 0,
        "E": 0,
        "W": 0,
    }


def test_traffic_density_calculation():
    sim = create_simulation()

    sim.vehicles = [
        Vehicle("N", sim.cx - 20, 100, 145),
        Vehicle("N", sim.cx - 20, 150, 145),
        Vehicle("S", sim.cx + 20, 500, 145),
    ]

    density = sim.traffic_density(500)

    assert density["N"] == 4
    assert density["S"] == 2
    assert density["E"] == 0
    assert density["W"] == 0


def test_traffic_density_invalid_segment_length():
    sim = create_simulation()

    import pytest

    with pytest.raises(ValueError):
        sim.traffic_density(0)

    with pytest.raises(ValueError):
        sim.traffic_density(-100)
