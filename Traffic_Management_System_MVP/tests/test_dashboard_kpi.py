"""TC-GUI-01 (TMS-F-016): dashboard KPIs refresh during execution."""
from simulation.metrics import Metrics
from interface.dashboard import build_kpi


def test_kpi_dict_keys_and_status():
    m = Metrics(spawned=20, completed=8, total_wait_seconds=40, elapsed_seconds=120)
    kpi = build_kpi(m, queue_len=3)
    assert kpi["active"] == 12
    assert kpi["generated"] == 20
    assert kpi["throughput"] == 8
    assert kpi["queue"] == 3
    assert kpi["status"] in ("FLOW OK", "CONGESTED")


def test_kpi_congested_reflects_state():
    m = Metrics(spawned=50, completed=5, total_wait_seconds=500, elapsed_seconds=120)
    kpi = build_kpi(m, queue_len=99)
    assert kpi["status"] == "CONGESTED"
