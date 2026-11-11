
"""Vehicle model and traffic simulation update logic."""
from dataclasses import dataclass
import random

DIRECTIONS = ("N", "S", "E", "W")


@dataclass
class Vehicle:
    direction: str
    x: float
    y: float
    speed: float
    length: float = 30.0
    width: float = 18.0
    wait_seconds: float = 0.0
    color: tuple = (50, 130, 220)
    road_id: str = ""

    def move(self, dt: float) -> None:
        distance = self.speed * dt
        if self.direction == "N":
            self.y += distance
        elif self.direction == "S":
            self.y -= distance
        elif self.direction == "W":
            self.x += distance
        else:
            self.x -= distance


class TrafficSimulation:
    def __init__(self, width: int, height: int, signals, metrics,
                 vehicle_speed=145.0, vehicle_length=30.0, vehicle_gap=13.0,
                 spawn_interval=1.25, seed=7, approaches=DIRECTIONS, road_ids=None):
        approaches = tuple(approaches)
        if not approaches or any(a not in DIRECTIONS for a in approaches) \
                or len(set(approaches)) != len(approaches):
            raise ValueError(f"approaches must be distinct values from {DIRECTIONS}")
        self.approaches = approaches
        self.road_ids = dict(road_ids or {a: f"R-{a}" for a in approaches})
        self.seed = seed
        self.width, self.height = width, height
        self.cx, self.cy = width / 2, height / 2
        self.road_half = 72
        self.signals = signals
        self.metrics = metrics
        self.vehicle_speed = vehicle_speed
        self.vehicle_length = vehicle_length
        self.vehicle_gap = vehicle_gap
        self.spawn_interval = spawn_interval
        self.spawn_elapsed = 0.0
        self.vehicles: list[Vehicle] = []
        self.rng = random.Random(seed)
        self.running_time = 0.0

    def reset(self) -> None:
        self.vehicles.clear()
        self.spawn_elapsed = 0.0
        self.running_time = 0.0
        self.metrics.spawned = 0
        self.metrics.completed = 0
        self.metrics.total_wait_seconds = 0.0
        self.metrics.waiting_vehicle_seconds = 0.0
        self.metrics.elapsed_seconds = 0.0
        self.signals.elapsed = 0.0
        self.signals.phase = "NS_GREEN"
        self.rng.seed(self.seed)  # reset reproduces the same arrival sequence

    def _spawn_position(self, direction):
        if direction == "N":
            return self.cx - 20, -35
        if direction == "S":
            return self.cx + 20, self.height + 35
        if direction == "W":
            return -35, self.cy + 20
        return self.width + 35, self.cy - 20

    def _can_spawn(self, direction) -> bool:
        x, y = self._spawn_position(direction)

        for car in self.vehicles:
            if car.direction != direction:
                continue

            if direction == "N" and car.y < 0 and abs(car.x - x) < 2 and abs(car.y - y) < self.vehicle_length + self.vehicle_gap:
                return False
            if direction == "S" and car.y > self.height and abs(car.x - x) < 2 and abs(car.y - y) < self.vehicle_length + self.vehicle_gap:
                return False
            if direction == "W" and car.x < 0 and abs(car.y - y) < 2 and abs(car.x - x) < self.vehicle_length + self.vehicle_gap:
                return False
            if direction == "E" and car.x > self.width and abs(car.y - y) < 2 and abs(car.x - x) < self.vehicle_length + self.vehicle_gap:
                return False

        return True

    def _spawn(self):
        directions = list(self.approaches)
        self.rng.shuffle(directions)

        for direction in directions:
            if self._can_spawn(direction):
                x, y = self._spawn_position(direction)
                color = self.rng.choice([
                    (45, 125, 220),
                    (235, 165, 45),
                    (70, 175, 115),
                    (180, 95, 190),
                    (220, 90, 85)
                ])

                self.vehicles.append(
                    Vehicle(
                        direction,
                        x,
                        y,
                        self.vehicle_speed,
                        self.vehicle_length,
                        color=color,
                        road_id=self.road_ids.get(direction, "")
                    )
                )
                self.metrics.spawned += 1
                break

    def _stop_limit(self, car):
        stop = self.road_half + 7

        if car.direction == "N":
            return self.cy - stop - car.length / 2
        if car.direction == "S":
            return self.cy + stop + car.length / 2
        if car.direction == "W":
            return self.cx - stop - car.length / 2

        return self.cx + stop + car.length / 2

    def _distance_to_stop(self, car):
        limit = self._stop_limit(car)

        if car.direction == "N":
            return limit - car.y
        if car.direction == "S":
            return car.y - limit
        if car.direction == "W":
            return limit - car.x

        return car.x - limit

    def _car_ahead_gap(self, car):
        gap = float("inf")

        for other in self.vehicles:
            if other is car or other.direction != car.direction:
                continue

            if car.direction == "N" and other.y > car.y:
                gap = min(gap, other.y - car.y - car.length)
            elif car.direction == "S" and other.y < car.y:
                gap = min(gap, car.y - other.y - car.length)
            elif car.direction == "W" and other.x > car.x:
                gap = min(gap, other.x - car.x - car.length)
            elif car.direction == "E" and other.x < car.x:
                gap = min(gap, car.x - other.x - car.length)

        return gap

    def _is_in_intersection(self, car):
        return (
            self.cx - self.road_half - car.length <= car.x <= self.cx + self.road_half + car.length
            and self.cy - self.road_half - car.length <= car.y <= self.cy + self.road_half + car.length
        )

    def _has_passed_stop_line(self, car):
        """True once the vehicle's front is beyond its stop line (committed to cross).

        The _is_in_intersection box starts 8px before the stop line, which let
        vehicles stopped in that gap drive through on red; movement uses this instead.
        """
        return self._distance_to_stop(car) < -0.01

    def update(self, dt: float):
        self.running_time += dt
        self.metrics.elapsed_seconds += dt
        self.spawn_elapsed += dt

        while self.spawn_elapsed >= self.spawn_interval:
            self.spawn_elapsed -= self.spawn_interval
            self._spawn()

        for car in list(self.vehicles):
            signal = self.signals.state_for(car.direction)
            distance = self._distance_to_stop(car)
            can_enter = signal == "GREEN" or self._has_passed_stop_line(car)
            proposed = self.vehicle_speed * dt

            if not can_enter and distance >= 0 and proposed >= distance:
                proposed = max(0.0, distance)

            ahead = self._car_ahead_gap(car)
            safe_gap = self.vehicle_gap

            if ahead < self.vehicle_length + safe_gap:
                proposed = min(
                    proposed,
                    max(0.0, ahead - safe_gap)
                )

            if proposed <= 0.01:
                car.wait_seconds += dt
                self.metrics.record_wait(dt)
                continue

            # A vehicle may approach the stop line but cannot cross it on amber/red.
            if signal != "GREEN" and not self._has_passed_stop_line(car) and distance <= proposed + 0.01:
                car.wait_seconds += dt
                self.metrics.record_wait(dt)
                continue

            car.move(proposed / self.vehicle_speed)

            if (
                car.x < -60
                or car.x > self.width + 60
                or car.y < -60
                or car.y > self.height + 60
            ):
                self.metrics.completed += 1
                self.metrics.total_wait_seconds += car.wait_seconds
                self.vehicles.remove(car)

    def queue_length(self) -> int:
        """
        Calculate the total number of vehicles waiting at the intersection.

        A vehicle is counted when it is within the queue detection range
        of its stop line and its signal is not green. The count is
        recalculated whenever this method is called.
        """
        queue_count = 0

        for car in self.vehicles:
            distance = self._distance_to_stop(car)

            is_within_queue_range = (
                -self.vehicle_length <= distance < 210
            )
            is_waiting_for_signal = (
                self.signals.state_for(car.direction) != "GREEN"
            )

            if is_within_queue_range and is_waiting_for_signal:
                queue_count += 1

        return queue_count

    def queue_lengths_by_direction(self) -> dict:
        """
        Return queued vehicle counts for each configured approach.

        A vehicle is counted when it is within the queue detection range
        of its stop line. Unlike queue_length(), this method reports each
        approach separately so adaptive signal control can compare demand.
        """
        queues = {direction: 0 for direction in self.approaches}

        for car in self.vehicles:
            distance = self._distance_to_stop(car)
            is_within_queue_range = (
                -self.vehicle_length <= distance < 210
            )

            if is_within_queue_range:
                queues[car.direction] += 1

        return queues

    def traffic_density(self, segment_length_m=500.0) -> dict:
        """
        Calculate traffic density for each road approach.

        Density = number of vehicles / road length in kilometres.

        Returns density in vehicles per kilometre.
        """
        if segment_length_m <= 0:
            raise ValueError("Segment length must be greater than zero.")

        segment_length_km = segment_length_m / 1000.0

        vehicle_counts = {
            direction: 0 for direction in DIRECTIONS
        }

        for car in self.vehicles:
            distance = self._distance_to_stop(car)

            if 0 <= distance <= segment_length_m:
                vehicle_counts[car.direction] += 1

        return {
            direction: count / segment_length_km
            for direction, count in vehicle_counts.items()
        }
