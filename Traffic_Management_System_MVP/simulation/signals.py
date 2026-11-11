
"""Traffic signal controller with fixed-time and adaptive modes."""
from dataclasses import dataclass, field


DEFAULT_PHASE_SEQUENCE = (
    "NS_GREEN",
    "NS_AMBER",
    "ALL_RED_TO_EW",
    "EW_GREEN",
    "EW_AMBER",
    "ALL_RED_TO_NS",
)


@dataclass
class SignalController:
    green_seconds: float = 12.0
    amber_seconds: float = 3.0
    red_clearance_seconds: float = 1.0
    elapsed: float = 0.0
    phase: str = "NS_GREEN"
    phase_sequence: tuple[str, ...] = field(
        default_factory=lambda: DEFAULT_PHASE_SEQUENCE
    )
    adaptive: bool = False
    min_green_seconds: float = 6.0
    max_green_seconds: float = 30.0

    _active_green_duration: float | None = field(
        default=None, init=False, repr=False
    )

    def __post_init__(self):
        if self.green_seconds <= 0:
            raise ValueError("green_seconds must be positive")
        if self.amber_seconds < 0 or self.red_clearance_seconds < 0:
            raise ValueError("Amber and red clearance durations cannot be negative")
        if self.min_green_seconds <= 0:
            raise ValueError("min_green_seconds must be positive")
        if self.max_green_seconds < self.min_green_seconds:
            raise ValueError(
                "max_green_seconds must be greater than or equal to min_green_seconds"
            )
        if not self.phase_sequence:
            raise ValueError("phase_sequence cannot be empty")

    @property
    def cycle_length(self) -> float:
        return 2 * (
            self.green_seconds
            + self.amber_seconds
            + self.red_clearance_seconds
        )

    def calculate_green_duration(self, queue_lengths: dict, directions: str) -> float:
        """Calculate green time from queue demand for NS or EW."""
        if not self.adaptive:
            return self.green_seconds

        if directions == "NS":
            demand = queue_lengths.get("N", 0) + queue_lengths.get("S", 0)
        else:
            demand = queue_lengths.get("E", 0) + queue_lengths.get("W", 0)

        # Add 1.5 seconds for each queued vehicle, within configured limits.
        duration = self.green_seconds + demand * 1.5

        return max(
            self.min_green_seconds,
            min(self.max_green_seconds, duration)
        )

    def update(self, dt: float, queue_lengths: dict | None = None) -> str | None:
        """Advance the controller and return a new phase after a transition."""
        if dt < 0:
            raise ValueError("dt cannot be negative")

        queue_lengths = queue_lengths or {}

        # Determine the duration when entering a green phase.
        if self.phase.endswith("_GREEN") and self._active_green_duration is None:
            directions = "NS" if self.phase == "NS_GREEN" else "EW"
            self._active_green_duration = self.calculate_green_duration(
                queue_lengths, directions
            )

        self.elapsed += dt
        duration = self._phase_duration()

        if self.elapsed >= duration:
            self.elapsed -= duration
            self.phase = self._next_phase()

            if self.phase.endswith("_GREEN"):
                directions = "NS" if self.phase == "NS_GREEN" else "EW"
                self._active_green_duration = self.calculate_green_duration(
                    queue_lengths, directions
                )
            else:
                self._active_green_duration = None

            return self.phase

        return None

    def _phase_duration(self) -> float:
        if self.phase.endswith("_GREEN"):
            if self.adaptive and self._active_green_duration is not None:
                return self._active_green_duration
            return self.green_seconds

        if self.phase.endswith("_AMBER"):
            return self.amber_seconds

        return self.red_clearance_seconds

    def _next_phase(self) -> str:
        """Return the next phase in the configured cycle."""
        try:
            current_index = self.phase_sequence.index(self.phase)
        except ValueError as exc:
            raise ValueError(
                f"Current phase {self.phase!r} is not in phase_sequence"
            ) from exc

        next_index = (current_index + 1) % len(self.phase_sequence)
        return self.phase_sequence[next_index]

    def state_for(self, direction: str) -> str:
        """Return GREEN, AMBER, or RED for N/S/E/W approaches."""
        if direction not in ("N", "S", "E", "W"):
            raise ValueError(f"Invalid direction: {direction!r}")

        ns = direction in ("N", "S")

        if self.phase == "NS_GREEN":
            return "GREEN" if ns else "RED"
        if self.phase == "NS_AMBER":
            return "AMBER" if ns else "RED"
        if self.phase == "EW_GREEN":
            return "GREEN" if not ns else "RED"
        if self.phase == "EW_AMBER":
            return "AMBER" if not ns else "RED"

        return "RED"

    def reset(self) -> None:
        """Restore the signal controller to its initial state."""
        self.elapsed = 0.0
        self.phase = self.phase_sequence[0]
        self._active_green_duration = None
