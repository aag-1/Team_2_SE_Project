
from simulation.metrics import Metrics
from simulation.signals import SignalController
from simulation.traffic import (
    EMERGENCY_COLOR,
    TrafficSimulation,
    Vehicle,
)


def create_traffic(emergency_probability=0.03):
    signals = SignalController(
        green_seconds=12,
        amber_seconds=3,
        red_clearance_seconds=1,
    )

    metrics = Metrics()

    traffic = TrafficSimulation(
        width=1100,
        height=760,
        signals=signals,
        metrics=metrics,
        seed=7,
        emergency_spawn_probability=emergency_probability,
        emergency_priority_distance=210,
    )

    return traffic, signals, metrics


def test_emergency_vehicle_is_identifiable():
    traffic, _, _ = create_traffic(emergency_probability=1.0)

    traffic._spawn()

    emergency_cars = [
        car for car in traffic.vehicles if car.is_emergency
    ]

    assert len(emergency_cars) == 1
    assert emergency_cars[0].color == EMERGENCY_COLOR


def test_normal_vehicle_spawns_when_emergency_probability_is_zero():
    traffic, _, _ = create_traffic(emergency_probability=0.0)

    traffic._spawn()

    assert len(traffic.vehicles) == 1
    assert traffic.vehicles[0].is_emergency is False


def test_emergency_vehicle_requests_priority():
    traffic, signals, _ = create_traffic()

    stop_line = traffic._stop_limit(
        Vehicle("N", traffic.cx - 20, 0, traffic.vehicle_speed)
    )

    emergency_car = Vehicle(
        direction="N",
        x=traffic.cx - 20,
        y=stop_line - 100,
        speed=traffic.vehicle_speed,
        color=EMERGENCY_COLOR,
        is_emergency=True,
    )

    traffic.vehicles.append(emergency_car)

    traffic._update_emergency_priority()

    assert signals.priority_direction == "N"


def test_emergency_priority_preserves_amber_and_all_red():
    signals = SignalController(
        green_seconds=12,
        amber_seconds=3,
        red_clearance_seconds=1,
    )

    # Start with east-west green.
    signals.phase = "EW_GREEN"
    signals.elapsed = 2

    # Emergency vehicle approaches from the north.
    signals.request_priority("N")

    # Current green should end early, but transition to amber first.
    transition = signals.update(0.1)

    assert transition == "EW_AMBER"
    assert signals.state_for("N") == "RED"
    assert signals.state_for("E") == "AMBER"

    # Amber must complete before all-red.
    transition = signals.update(3.0)

    assert transition == "ALL_RED_TO_NS"
    assert signals.state_for("N") == "RED"
    assert signals.state_for("E") == "RED"

    # All-red clearance must complete before north-south green.
    transition = signals.update(1.0)

    assert transition == "NS_GREEN"
    assert signals.state_for("N") == "GREEN"


def test_priority_is_cancelled_after_emergency_vehicle_clears():
    traffic, signals, _ = create_traffic()

    signals.request_priority("N")

    emergency_car = Vehicle(
        direction="N",
        x=traffic.cx - 20,
        y=traffic.height + 100,
        speed=traffic.vehicle_speed,
        color=EMERGENCY_COLOR,
        is_emergency=True,
    )

    traffic.vehicles.append(emergency_car)

    traffic._update_emergency_priority()

    assert signals.priority_direction is None


def test_reset_clears_emergency_priority():
    traffic, signals, _ = create_traffic()

    signals.request_priority("N")

    traffic.reset()

    assert signals.priority_direction is None
    assert traffic.vehicles == []
