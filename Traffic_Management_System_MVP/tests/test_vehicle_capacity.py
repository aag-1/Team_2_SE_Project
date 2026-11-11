
from simulation.traffic import TrafficSimulation, Vehicle


class FakeSignals:
    def state_for(self, direction):
        return "GREEN"

    def request_priority(self, direction):
        pass

    def cancel_priority(self):
        pass


class FakeMetrics:
    def __init__(self):
        self.spawned = 0
        self.completed = 0
        self.total_wait_seconds = 0.0
        self.waiting_vehicle_seconds = 0.0
        self.elapsed_seconds = 0.0

    def record_wait(self, dt):
        self.waiting_vehicle_seconds += dt


def test_simulation_supports_500_simultaneous_vehicles():
    metrics = FakeMetrics()

    simulation = TrafficSimulation(
        width=10000,
        height=10000,
        signals=FakeSignals(),
        metrics=metrics,
        vehicle_speed=145,
        spawn_interval=10000,
    )

    # Add 125 vehicles on each of the four approaches.
    for direction in ("N", "S", "E", "W"):
        for i in range(125):
            position = 1000 + i * 45

            if direction == "N":
                x, y = 4980, position
            elif direction == "S":
                x, y = 5020, 9000 - position
            elif direction == "W":
                x, y = position, 5020
            else:
                x, y = 9000 - position, 4980

            simulation.vehicles.append(
                Vehicle(
                    direction=direction,
                    x=x,
                    y=y,
                    speed=145,
                )
            )

    assert len(simulation.vehicles) == 500

    # Advance the simulation and verify all vehicles remain manageable.
    simulation.update(1 / 60)

    assert len(simulation.vehicles) == 500
