"""Fixed-time traffic signal controller."""
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

    @property
    def cycle_length(self) -> float:
        return 2 * (
            self.green_seconds
            + self.amber_seconds
            + self.red_clearance_seconds
        )

    def update(self, dt: float) -> str | None:
        """Advance the controller and return a new phase after a transition."""
        if dt < 0:
            raise ValueError("dt cannot be negative")

        self.elapsed += dt
        duration = self._phase_duration()

        if self.elapsed >= duration:
            self.elapsed -= duration
            self.phase = self._next_phase()
            return self.phase

        return None

    def _phase_duration(self) -> float:
        if self.phase.endswith("_GREEN"):
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