
from simulation.metrics import Metrics
from simulation.traffic import TrafficSimulation, Vehicle


class MockSignals:
    def __init__(self, state="RED"):
        self.state = state

    def state_for(self, direction):
        return self.state


def create_simulation(signal_state="RED"):
    signals = MockSignals(signal_state)
    metrics = Metrics()

    return TrafficSimulation(
        width=800,
        height=600,
        signals=signals,
        metrics=metrics
    )


def test_queue_length_is_zero_when_no_vehicles():
    sim = create_simulation()

    assert sim.queue_length() == 0


def test_queue_length_counts_vehicles_waiting_at_red_signal():
    sim = create_simulation()

    sim.vehicles = [
        Vehicle("N", sim.cx - 20, 100, 145),
        Vehicle("S", sim.cx + 20, 500, 145),
    ]

    assert sim.queue_length() == 2


def test_queue_length_is_zero_when_signal_is_green():
    sim = create_simulation(signal_state="GREEN")

    sim.vehicles = [
        Vehicle("N", sim.cx - 20, 100, 145),
        Vehicle("S", sim.cx + 20, 500, 145),
    ]

    assert sim.queue_length() == 0


def test_queue_length_counts_vehicles_at_amber_signal():
    sim = create_simulation(signal_state="AMBER")

    sim.vehicles = [
        Vehicle("N", sim.cx - 20, 100, 145)
    ]

    assert sim.queue_length() == 1


def test_queue_length_updates_when_vehicle_joins_queue():
    sim = create_simulation()

    assert sim.queue_length() == 0

    car = Vehicle("N", sim.cx - 20, 100, 145)
    sim.vehicles.append(car)

    assert sim.queue_length() == 1


def test_queue_length_updates_when_vehicle_leaves_queue():
    sim = create_simulation()

    car = Vehicle("N", sim.cx - 20, 100, 145)
    sim.vehicles.append(car)

    assert sim.queue_length() == 1

    sim.vehicles.remove(car)

    assert sim.queue_length() == 0


def test_queue_length_excludes_vehicles_outside_detection_range():
    sim = create_simulation()

    car = Vehicle("N", sim.cx - 20, -10, 145)
    sim.vehicles.append(car)

    assert sim.queue_length() == 0
