
from simulation.metrics import Metrics


def test_throughput_calculation():
    metrics = Metrics(
        spawned=20,
        completed=10,
        elapsed_seconds=120
    )

    assert metrics.throughput_per_minute == 5.0


def test_throughput_with_no_completed_vehicles():
    metrics = Metrics(
        spawned=10,
        completed=0,
        elapsed_seconds=60
    )

    assert metrics.throughput_per_minute == 0.0


def test_throughput_with_zero_elapsed_time():
    metrics = Metrics(
        spawned=10,
        completed=5,
        elapsed_seconds=0
    )

    assert metrics.throughput_per_minute == 0.0


def test_throughput_updates_when_vehicle_completes():
    metrics = Metrics(
        spawned=10,
        completed=2,
        elapsed_seconds=60
    )

    assert metrics.throughput_per_minute == 2.0

    metrics.completed = 5

    assert metrics.throughput_per_minute == 5.0


def test_throughput_updates_as_simulation_time_increases():
    metrics = Metrics(
        spawned=10,
        completed=5,
        elapsed_seconds=60
    )

    assert metrics.throughput_per_minute == 5.0

    metrics.elapsed_seconds = 120

    assert metrics.throughput_per_minute == 2.5
