"""TC-VEH-02 (TMS-F-004): vehicles move according to valid route and signal conditions."""
from simulation.engine import SimulationEngine
from simulation.scenario import create_scenario

DT = 1 / 30


def run(engine, seconds, each=None):
    for _ in range(round(seconds / DT)):
        engine.tick(DT)
        if each:
            each(engine)


def test_red_approaches_never_cross_stop_line(default_scenario):
    engine = SimulationEngine(default_scenario)  # starts NS_GREEN, so E/W are red

    def check(e):
        assert e.signals.phase == "NS_GREEN"
        for car in e.traffic.vehicles:
            if car.direction in ("E", "W"):
                assert e.traffic._distance_to_stop(car) >= -0.01, "crossed on red"

    run(engine, 11.5, check)
    assert any(c.direction in ("E", "W") for c in engine.traffic.vehicles), \
        "test needs queued E/W vehicles to be meaningful"


def test_green_approaches_cross_and_complete_route(default_scenario):
    engine = SimulationEngine(default_scenario)
    run(engine, 11.5)
    assert engine.metrics.completed > 0
    # waiting E/W vehicles get through after the phase change
    run(engine, 32)
    assert engine.signals.phase.startswith(("EW", "ALL_RED", "NS"))
    assert engine.metrics.completed >= 10


def test_vehicles_stay_in_their_lane_and_keep_direction(default_scenario):
    engine = SimulationEngine(default_scenario)
    start = {}

    def check(e):
        for car in e.traffic.vehicles:
            key = id(car)
            if key not in start or start[key][0] is not car:  # id() can be reused
                start[key] = (car, car.direction, car.x, car.y)
            _, direction, x0, y0 = start[key]
            assert car.direction == direction
            if direction in ("N", "S"):
                assert car.x == x0
            else:
                assert car.y == y0
            # never moves backwards along its route
            delta = {"N": car.y - y0, "S": y0 - car.y, "W": car.x - x0, "E": x0 - car.x}
            assert delta[direction] >= 0

    run(engine, 60, check)


def test_vehicles_on_same_road_never_overlap(default_scenario):
    engine = SimulationEngine(default_scenario)
    engine.set_spawn_interval(0.25)  # heavy traffic

    def check(e):
        by_road = {}
        for car in e.traffic.vehicles:
            by_road.setdefault(car.direction, []).append(car)
        for direction, cars in by_road.items():
            axis = "y" if direction in ("N", "S") else "x"
            positions = sorted(getattr(c, axis) for c in cars)
            for a, b in zip(positions, positions[1:]):
                assert b - a >= e.traffic.vehicle_length - 0.01, f"overlap on {direction}"

    run(engine, 120, check)


def test_only_configured_roads_generate_traffic():
    scenario = create_scenario("Two roads", approaches=["N", "E"])
    engine = SimulationEngine(scenario)
    seen = set()
    run(engine, 60, lambda e: seen.update((c.direction, c.road_id) for c in e.traffic.vehicles))
    assert seen == {("N", "R-N"), ("E", "R-E")}


def test_no_vehicle_crosses_stop_line_on_red_or_amber_over_full_cycles(default_scenario):
    """Regression for the 8px gap bug: checked on every approach for 10 minutes."""
    engine = SimulationEngine(default_scenario)
    engine.set_spawn_interval(0.25)
    crossings_on_green = 0
    for _ in range(round(600 / DT)):
        before = {id(c): (c, engine.traffic._distance_to_stop(c)) for c in engine.traffic.vehicles}
        engine.tick(DT)
        for car, dist_before in before.values():
            if car not in engine.traffic.vehicles or dist_before < -0.01:
                continue
            crossed = engine.traffic._distance_to_stop(car) < -0.01
            state = engine.signals.state_for(car.direction)
            if crossed:
                assert state == "GREEN", f"{car.direction} vehicle crossed on {state}"
                crossings_on_green += 1
    assert crossings_on_green > 100
