"""TC-VEH-01 (TMS-F-003): vehicle generation follows selected rate."""
from simulation.signals import SignalController
from simulation.metrics import Metrics
from simulation.traffic import TrafficSimulation


def make_sim(spawn_interval=0.5, seed=7):
    signals = SignalController()
    metrics = Metrics()
    return TrafficSimulation(1100, 760, signals, metrics, spawn_interval=spawn_interval, seed=seed)


def test_spawn_interval_clamp():
    sim = make_sim()
    assert sim.set_spawn_interval(0.01) == 0.25
    assert sim.set_spawn_interval(99) == 5.0
    assert sim.set_spawn_interval(1.0) == 1.0


def test_vehicles_generate_over_time():
    sim = make_sim(spawn_interval=0.25)
    sim.update(2.0)
    assert sim.metrics.spawned > 0
    assert sim.spawn_count == sim.metrics.spawned


def test_faster_rate_spawns_more():
    slow = make_sim(spawn_interval=5.0, seed=7)
    fast = make_sim(spawn_interval=0.25, seed=7)
    slow.update(5.0)
    fast.update(5.0)
    assert fast.metrics.spawned >= slow.metrics.spawned
