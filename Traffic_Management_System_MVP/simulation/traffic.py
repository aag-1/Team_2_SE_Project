
"""Vehicle model and traffic simulation update logic."""
from dataclasses import dataclass
import random

DIRECTIONS = ("N", "S", "E", "W")
EMERGENCY_COLOR = (255, 40, 40)


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
    is_emergency: bool = False

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
    def __init__(
        self,
        width: int,
        height: int,
        signals,
        metrics,
        vehicle_speed=145.0,
        vehicle_length=30.0,
        vehicle_gap=13.0,
        spawn_interval=1.25,
        seed=7,
        approaches=DIRECTIONS,
        road_ids=None,
        emergency_spawn_probability=0.03,
        emergency_priority_distance=210.0,
    ):
        approaches = tuple(approaches)

        if (
            not approaches
            or any(a not in DIRECTIONS for a in approaches)
            or len(set(approaches)) != len(approaches)
        ):
            raise ValueError(
                f"approaches must be distinct values from {DIRECTIONS}"
            )

        if not 0.0 <= emergency_spawn_probability <= 1.0:
            raise ValueError(
                "emergency_spawn_probability must be between 0 and 1"
            )

        if emergency_priority_distance <= 0:
            raise ValueError(
                "emergency_priority_distance must be greater than zero"
            )

        self.approaches = approaches
        self.road_ids = dict(
            road_ids or {a: f"R-{a}" for a in approaches}
        )

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

        self.emergency_spawn_probability = emergency_spawn_probability
        self.emergency_priority_distance = emergency_priority_distance

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
        self.signals.phase = self.signals.phase_sequence[0]
        self.signals.cancel_priority()

        if hasattr(self.signals, "_active_green_duration"):
            self.signals._active_green_duration = None

        self.rng.seed(self.seed)

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

            if (
                direction == "N"
                and car.y < 0
                and abs(car.x - x) < 2
                and abs(car.y - y) < self.vehicle_length + self.vehicle_gap
            ):
                return False

            if (
                direction == "S"
                and car.y > self.height
                and abs(car.x - x) < 2
                and abs(car.y - y) < self.vehicle_length + self.vehicle_gap
            ):
                return False

            if (
                direction == "W"
                and car.x < 0
                and abs(car.y - y) < 2
                and abs(car.x - x) < self.vehicle_length + self.vehicle_gap
            ):
                return False

            if (
                direction == "E"
                and car.x > self.width
                and abs(car.y - y) < 2
                and abs(car.x - x) < self.vehicle_length + self.vehicle_gap
            ):
                return False

        return True

    def _spawn(self):
        directions = list(self.approaches)
        self.rng.shuffle(directions)

        for direction in directions:
            if self._can_spawn(direction):
                x, y = self._spawn_position(direction)

                is_emergency = (
                    self.emergency_spawn_probability > 0
                    and self.rng.random() < self.emergency_spawn_probability
                )

                if is_emergency:
                    color = EMERGENCY_COLOR
                else:
                    color = self.rng.choice([
                        (45, 125, 220),
                        (235, 165, 45),
                        (70, 175, 115),
                        (180, 95, 190),
                        (220, 90, 85),
                    ])

                self.vehicles.append(
                    Vehicle(
                        direction=direction,
                        x=x,
                        y=y,
                        speed=self.vehicle_speed,
                        length=self.vehicle_length,
                        color=color,
                        road_id=self.road_ids.get(direction, ""),
                        is_emergency=is_emergency,
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
            self.cx - self.road_half - car.length
            <= car.x
            <= self.cx + self.road_half + car.length
            and
            self.cy - self.road_half - car.length
            <= car.y
            <= self.cy + self.road_half + car.length
        )

    def _has_passed_stop_line(self, car):
        """Return True once the vehicle has crossed its stop line."""
        return self._distance_to_stop(car) < -0.01

    def _update_emergency_priority(self):
        """Request signal priority for an approaching emergency vehicle."""

        emergency_vehicles = [
            car for car in self.vehicles
            if car.is_emergency
        ]

        approaching = []

        for car in emergency_vehicles:
            distance = self._distance_to_stop(car)

            if (
                distance <= self.emergency_priority_distance
                and (
                    distance >= -self.vehicle_length
                    or self._is_in_intersection(car)
                )
            ):
                approaching.append(car)

        if approaching:
            # Give priority to the nearest emergency vehicle.
            priority_car = min(
                approaching,
                key=lambda car: abs(self._distance_to_stop(car))
            )

            self.signals.request_priority(priority_car.direction)

        else:
            # Resume normal/adaptive signal operation.
            self.signals.cancel_priority()


    def update(self, dt: float):
        self.running_time += dt
        self.metrics.elapsed_seconds += dt
        self.spawn_elapsed += dt

        while self.spawn_elapsed >= self.spawn_interval:
            self.spawn_elapsed -= self.spawn_interval
            self._spawn()

        # Check for approaching emergency vehicles.
        self._update_emergency_priority()

        # Group vehicles by direction and sort front-to-back.
        vehicles_by_direction = {
            direction: [] for direction in DIRECTIONS
        }

        for car in self.vehicles:
            vehicles_by_direction[car.direction].append(car)

        sort_keys = {
            "N": lambda car: -car.y,
            "S": lambda car: car.y,
            "W": lambda car: -car.x,
            "E": lambda car: car.x,
        }

        survivors = []

        for direction, cars in vehicles_by_direction.items():
            cars.sort(key=sort_keys[direction])
            previous_car = None

            for car in cars:
                signal = self.signals.state_for(car.direction)
                distance = self._distance_to_stop(car)

                can_enter = (
                    signal == "GREEN"
                    or self._has_passed_stop_line(car)
                )

                proposed = self.vehicle_speed * dt

                if not can_enter and distance >= 0 and proposed >= distance:
                    proposed = max(0.0, distance)

                # Check only the nearest surviving vehicle ahead.
                if previous_car is not None:
                    if direction == "N":
                        ahead = (
                            previous_car.y - car.y - car.length
                        )
                    elif direction == "S":
                        ahead = (
                            car.y - previous_car.y - car.length
                        )
                    elif direction == "W":
                        ahead = (
                            previous_car.x - car.x - car.length
                        )
                    else:
                        ahead = (
                            car.x - previous_car.x - car.length
                        )

                    if ahead < self.vehicle_length + self.vehicle_gap:
                        proposed = min(
                            proposed,
                            max(0.0, ahead - self.vehicle_gap)
                        )

                if proposed <= 0.01:
                    car.wait_seconds += dt
                    self.metrics.record_wait(dt)
                    survivors.append(car)
                    previous_car = car
                    continue

                # Vehicles cannot cross the stop line on amber or red.
                if (
                    signal != "GREEN"
                    and not self._has_passed_stop_line(car)
                    and distance <= proposed + 0.01
                ):
                    car.wait_seconds += dt
                    self.metrics.record_wait(dt)
                    survivors.append(car)
                    previous_car = car
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
                    continue

                survivors.append(car)
                previous_car = car

        # Replace the vehicle list once instead of removing cars individually.
        self.vehicles = survivors

    def queue_length(self) -> int:
        """
        Calculate the total number of vehicles waiting at the intersection.
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
        """
        queues = {
            direction: 0 for direction in self.approaches
        }

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
            raise ValueError(
                "Segment length must be greater than zero."
            )

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
