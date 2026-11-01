"""TC-INC-01 (TMS-F-014): incident changes traffic state, visible to operator."""
from simulation.signals import SignalController
from simulation.metrics import Metrics
from simulation.traffic import TrafficSimulation
from simulation.incident import IncidentManager


def test_trigger_and_clear():
    inc = IncidentManager()
    assert not inc.active
    assert inc.trigger(["N"], "Stalled N")
    assert inc.active
    assert inc.is_blocked("N")
    assert not inc.is_blocked("E")
    assert "INCIDENT" in inc.banner()
    inc.clear()
    assert not inc.active


def test_invalid_direction_rejected():
    inc = IncidentManager()
    assert not inc.trigger(["X"])


def test_incident_blocks_spawning():
    signals = SignalController()
    metrics = Metrics()
    inc = IncidentManager()
    inc.trigger(["N", "S", "E", "W"], "Full closure")
    sim = TrafficSimulation(1100, 760, signals, metrics, spawn_interval=0.25,
                            seed=1, incident_manager=inc)
    sim.update(2.0)
    # all directions blocked -> no spawns from blocked approaches
    assert sim.metrics.spawned == 0
    inc.clear()
    sim.update(2.0)
    assert sim.metrics.spawned > 0
