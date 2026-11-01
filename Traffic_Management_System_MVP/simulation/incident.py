"""Traffic incident simulation (TMS-F-014, TC-INC-01).

Blocked direction(s) or stalled vehicle: incident changes traffic state
and is visible to operator via dashboard INCIDENT banner.
Local-only, no external sensors.
"""
from __future__ import annotations

DIRECTIONS = ("N", "S", "E", "W")


class IncidentManager:
    """Track one active incident at a time (minimal demo scope)."""

    def __init__(self) -> None:
        self.active: bool = False
        self.blocked_directions: set[str] = set()
        self.description: str = ""

    def trigger(self, blocked: list[str] | str, description: str = "") -> bool:
        dirs = [blocked] if isinstance(blocked, str) else list(blocked)
        dirs = [d for d in dirs if d in DIRECTIONS]
        if not dirs:
            return False
        self.active = True
        self.blocked_directions = set(dirs)
        self.description = description or f"Blocked: {','.join(sorted(dirs))}"
        return True

    def clear(self) -> None:
        self.active = False
        self.blocked_directions.clear()
        self.description = ""

    def is_blocked(self, direction: str) -> bool:
        return self.active and direction in self.blocked_directions

    def banner(self) -> str:
        if not self.active:
            return ""
        return f"INCIDENT: {self.description}"
