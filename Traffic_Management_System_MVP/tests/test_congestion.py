"""TC-CON-01 (TMS-F-010): congestion alert when threshold exceeded."""
from simulation.congestion import is_congested, status_label


def test_no_congestion_when_low():
    congested, _ = is_congested(2, 1.0, 5)
    assert not congested
    assert status_label(2, 1.0, 5) == "FLOW OK"


def test_congestion_on_queue():
    congested, reason = is_congested(99, 1.0, 5)
    assert congested
    assert "queue" in reason


def test_congestion_on_wait():
    congested, _ = is_congested(2, 99.0, 5)
    assert congested
    assert status_label(2, 99.0, 5) == "CONGESTED"


def test_custom_thresholds():
    th = {"queue_length": 100, "avg_wait_seconds": 100.0, "active_vehicles": 100}
    assert not is_congested(50, 50.0, 50, th)[0]
