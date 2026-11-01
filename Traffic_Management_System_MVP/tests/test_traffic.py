from simulation.metrics import Metrics
from simulation.signals import SignalController
from simulation.traffic import TrafficSimulation, Vehicle


def make_simulation():
    signals = SignalController()
    metrics = Metrics()

    sim = TrafficSimulation(
        width=800,
        height=600,
        signals=signals,
        metrics=metrics,
        vehicle_speed=100,
        vehicle_length=30,
        vehicle_gap=13,
        spawn_interval=1000,
    )

    return sim, signals, metrics


def make_northbound_vehicle(sim, distance_before_stop=30):
    stop_limit = sim._stop_limit(
        Vehicle(direction="N", x=sim.cx - 20, y=0, speed=100)
    )

    return Vehicle(
        direction="N",
        x=sim.cx - 20,
        y=stop_limit - distance_before_stop,
        speed=100,
    )


def test_vehicle_stops_at_red_signal():
    sim, signals, metrics = make_simulation()
    signals.phase = "EW_GREEN"

    car = make_northbound_vehicle(sim, distance_before_stop=30)
    sim.vehicles.append(car)

    sim.update(0.5)

    assert sim._distance_to_stop(car) >= -0.01
    assert car.wait_seconds > 0


def test_vehicle_can_move_on_green_signal():
    sim, signals, metrics = make_simulation()
    signals.phase = "NS_GREEN"

    car = make_northbound_vehicle(sim, distance_before_stop=30)
    sim.vehicles.append(car)

    initial_y = car.y
    sim.update(0.1)

    assert car.y > initial_y


def test_vehicle_waits_at_amber_signal():
    sim, signals, metrics = make_simulation()
    signals.phase = "NS_AMBER"

    car = make_northbound_vehicle(sim, distance_before_stop=30)
    sim.vehicles.append(car)

    sim.update(0.5)

    assert sim._distance_to_stop(car) >= -0.01
    assert car.wait_seconds > 0
    assert metrics.waiting_vehicle_seconds > 0