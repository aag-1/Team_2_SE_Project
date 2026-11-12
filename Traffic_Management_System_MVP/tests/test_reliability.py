"""TC-NF-03 (TMS-NF-003): 5 consecutive 30-minute simulated runs without failure."""
import pytest

from simulation.scenario import create_scenario
from tools.reliability_run import main as reliability_main, run_once


def test_five_consecutive_thirty_minute_runs(default_scenario):
    results = [run_once(default_scenario, minutes=30, run_no=n) for n in range(1, 6)]
    for r in results:
        assert r["ok"], r["problems"]
        assert r["sim_seconds"] == pytest.approx(1800, abs=0.05)
    assert sum(r["ok"] for r in results) == 5          # 100% completion


def test_thirty_minutes_under_maximum_traffic():
    heavy = create_scenario("Max load", spawn_interval_seconds=0.25)
    result = run_once(heavy, minutes=30, run_no=1)
    assert result["ok"], result["problems"]


def test_reliability_cli_reports_success(capsys):
    assert reliability_main(["--runs", "2", "--minutes", "1"]) == 0
    assert "2/2 runs completed" in capsys.readouterr().out
