"""TC-CTL-01 (TMS-F-015): pause, resume, step and reset produce the expected state."""
import pytest

from simulation.engine import PAUSED, RUNNING, STEP_SECONDS, SimulationEngine

DT = 1 / 30


def positions(engine):
    return [(c.direction, round(c.x, 6), round(c.y, 6)) for c in engine.traffic.vehicles]


def advance(engine, seconds):
    for _ in range(round(seconds / DT)):
        engine.tick(DT)


def test_pause_freezes_clock_vehicles_and_signals(default_scenario):
    engine = SimulationEngine(default_scenario)
    advance(engine, 5)
    engine.pause()
    frozen = (engine.clock, positions(engine), engine.signals.phase, engine.signals.elapsed)
    for _ in range(300):
        assert engine.tick(DT) is False
    assert engine.state == PAUSED
    assert (engine.clock, positions(engine), engine.signals.phase,
            engine.signals.elapsed) == frozen


def test_resume_continues_from_paused_state(default_scenario):
    engine = SimulationEngine(default_scenario)
    advance(engine, 5)
    engine.pause()
    clock = engine.clock
    engine.resume()
    assert engine.state == RUNNING
    assert engine.tick(DT) is True
    assert engine.clock == pytest.approx(clock + DT)


def test_step_advances_exactly_one_tick_only_while_paused(default_scenario):
    engine = SimulationEngine(default_scenario)
    assert engine.step() is False and engine.clock == 0  # ignored while running
    engine.pause()
    assert engine.step() is True
    assert engine.clock == pytest.approx(STEP_SECONDS)
    assert engine.tick_count == 1
    assert engine.state == PAUSED


def test_step_matches_normal_ticks(default_scenario):
    """Stepping N times must give the same state as running N ticks (same update order)."""
    a, b = SimulationEngine(default_scenario), SimulationEngine(default_scenario, start_paused=True)
    for _ in range(600):
        a.tick(STEP_SECONDS)
        b.step(STEP_SECONDS)
    assert positions(a) == positions(b)
    assert a.snapshot() == b.snapshot()


def test_reset_restores_initial_state(default_scenario):
    engine = SimulationEngine(default_scenario)
    engine.set_spawn_interval(0.4)
    advance(engine, 40)
    assert engine.metrics.spawned > 0
    engine.reset()
    assert engine.clock == 0 and engine.tick_count == 0
    assert engine.traffic.vehicles == []
    assert engine.signals.phase == "NS_GREEN" and engine.signals.elapsed == 0
    assert (engine.metrics.spawned, engine.metrics.completed,
            engine.metrics.total_wait_seconds) == (0, 0, 0)
    assert engine.traffic.spawn_interval == default_scenario.simulation["spawn_interval_seconds"]


def test_reset_is_reproducible(default_scenario):
    engine = SimulationEngine(default_scenario)
    advance(engine, 45)
    first = engine.snapshot()
    engine.reset()
    advance(engine, 45)
    assert engine.snapshot() == first


def test_reset_keeps_pause_state(default_scenario):
    engine = SimulationEngine(default_scenario)
    engine.pause()
    engine.reset()
    assert engine.state == PAUSED


def test_controls_emit_events(default_scenario):
    engine = SimulationEngine(default_scenario)
    seen = []
    engine.add_listener(lambda kind, msg, ctx: seen.append((kind, msg)))
    engine.pause(); engine.step(); engine.resume(); engine.reset()
    messages = [m for _, m in seen]
    assert messages[0] == "Simulation paused"
    assert messages[1].startswith("Stepped")
    assert messages[2:] == ["Simulation resumed", "Simulation reset"]


@pytest.mark.parametrize("bad", [0, -1, float("nan"), float("inf"), "1", None, True])
def test_invalid_tick_duration_rejected(default_scenario, bad):
    engine = SimulationEngine(default_scenario)
    with pytest.raises(ValueError):
        engine.tick(bad)
