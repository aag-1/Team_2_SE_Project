"""Event log for significant simulation events and errors (TMS-F-020).

Each event has timestamp (ISO-8601), type, and context dict.
Supports in-memory list + JSONL export. No external deps.
"""
from __future__ import annotations
from datetime import datetime, timezone
import json
from pathlib import Path


class EventLogger:
    """Minimal timestamped event log (TC-LOG-01)."""

    def __init__(self) -> None:
        self.events: list[dict] = []

    def log(self, event_type: str, context: dict | None = None) -> dict:
        """Record an event. Always includes timestamp, type, context."""
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "type": str(event_type),
            "context": dict(context or {}),
        }
        self.events.append(entry)
        return entry

    def error(self, message: str, context: dict | None = None) -> dict:
        ctx = dict(context or {})
        ctx["message"] = message
        return self.log("ERROR", ctx)

    def clear(self) -> None:
        self.events.clear()

    def __len__(self) -> int:
        return len(self.events)

    def to_jsonl(self) -> str:
        return "\n".join(json.dumps(e) for e in self.events)

    def save_jsonl(self, path: str | Path) -> Path:
        p = Path(path)
        p.write_text(self.to_jsonl() + ("\n" if self.events else ""), encoding="utf-8")
        return p

    @classmethod
    def load_jsonl(cls, path: str | Path) -> "EventLogger":
        logger = cls()
        for line in Path(path).read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                logger.events.append(json.loads(line))
        return logger
