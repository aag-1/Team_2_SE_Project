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
