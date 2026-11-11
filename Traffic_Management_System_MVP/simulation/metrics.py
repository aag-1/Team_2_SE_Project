"""Small collection of simulation KPI calculations."""
from dataclasses import dataclass


@dataclass
class Metrics:
    spawned: int = 0
    completed: int = 0
    total_wait_seconds: float = 0.0
    total_travel_seconds: float = 0.0
    waiting_vehicle_seconds: float = 0.0
    elapsed_seconds: float = 0.0

    @property
    def active_count(self) -> int:
        return max(0, self.spawned - self.completed)

    @property
    def throughput_per_minute(self) -> float:
        if self.elapsed_seconds <= 0:
            return 0.0
        return self.completed * 60.0 / self.elapsed_seconds

    @property
    def average_wait_seconds(self) -> float:
        if self.completed <= 0:
            return 0.0
        return self.total_wait_seconds / self.completed

    @property
    def average_delay_seconds(self) -> float:
        return self.average_wait_seconds

    @property
    def average_travel_time_seconds(self) -> float:
        if self.completed <= 0:
            return 0.0
        return self.total_travel_seconds / self.completed

    def record_wait(self, dt: float) -> None:
        self.waiting_vehicle_seconds += dt
