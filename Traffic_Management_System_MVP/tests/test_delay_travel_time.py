from simulation.metrics import Metrics
from simulation.traffic import TrafficSimulation, Vehicle
from simulation.signals import SignalController


def make_simulation():
    metrics = Metrics()
    signals = SignalController(
        green_seconds=10,
        amber_seconds=2,
        red_clearance_seconds=1,
    )
    sim = TrafficSimulation(
        width=800,
        height=600,
        signals=signals,
        metrics=metrics,
        emergency_spawn_probability=0,
    )
    return sim, metrics


def test_average_delay_uses_completed_vehicles():
    metrics = Metrics(completed=4, total_wait_seconds=20)
    assert metrics.average_delay_seconds == 5


def test_average_travel_time_uses_completed_vehicles():
    metrics = Metrics(completed=4, total_travel_seconds=100)
    assert metrics.average_travel_time_seconds == 25


def test_averages_are_zero_without_completed_vehicles():
    metrics = Metrics()
    assert metrics.average_delay_seconds == 0
    assert metrics.average_travel_time_seconds == 0


def test_vehicle_travel_time_increases_during_simulation():
    sim, _ = make_simulation()
    car = Vehicle(
        direction="N",
        x=sim.cx - 20,
        y=sim.cy,
        speed=sim.vehicle_speed,
    )
    sim.vehicles.append(car)

    sim.update(0.5)

    assert car.travel_seconds == 0.5


def test_completed_vehicle_contributes_to_total_travel_time():
    sim, metrics = make_simulation()
    car = Vehicle(
        direction="N",
        x=sim.cx - 20,
        y=sim.height + 61,
        speed=sim.vehicle_speed,
        wait_seconds=3,
        travel_seconds=12,
    )
    sim.vehicles.append(car)

    sim.update(0.1)

    assert metrics.completed == 1
    assert metrics.total_wait_seconds == 3
    assert metrics.total_travel_seconds == 12.1
    assert metrics.average_travel_time_seconds == 12.1


def test_reset_clears_travel_time_metrics():
    sim, metrics = make_simulation()
    metrics.total_travel_seconds = 120
    metrics.completed = 3

    sim.reset()

    assert metrics.total_travel_seconds == 0
    assert metrics.completed == 0
    assert metrics.average_travel_time_seconds == 0