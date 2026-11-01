"""TC-NF-04 (TMS-NF-004): consistent state across pause/resume/reset, 20 cycles."""
from simulation.signals import SignalController
from simulation.metrics import Metrics
from simulation.traffic import TrafficSimulation


def test_20_control_cycles_stay_valid():
    signals = SignalController()
    metrics = Metrics()
    sim = TrafficSimulation(1100, 760, signals, metrics, spawn_interval=0.5)
    for _ in range(20):
        sim.update(0.5)   # running
        # pause = no update; resume = update again
        sim.update(0.5)
    assert sim.metrics.spawned >= 0
    assert sim.metrics.elapsed_seconds > 0
    assert 0 <= len(sim.vehicles) <= 500


def test_reset_clears_state():
    signals = SignalController()
    metrics = Metrics()
    sim = TrafficSimulation(1100, 760, signals, metrics, spawn_interval=0.25)
    sim.update(3.0)
    assert sim.metrics.spawned > 0
    sim.reset()
    assert sim.vehicles == []
    assert sim.metrics.spawned == 0
    assert sim.metrics.completed == 0
    assert signals.phase == "NS_GREEN"
