
"""Persistent security audit logging for TMS-SR-005."""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_AUDIT_DIR = (
    Path(__file__).resolve().parents[1] / "logs"
)


class SecurityAuditLogger:
    """Writes security-relevant events to a JSON Lines audit file."""

    VALID_EVENTS = {
        "AUTHENTICATION_FAILED",
        "ADMIN_ACTION_DENIED",
    }

    def __init__(self, log_dir: Path | str = DEFAULT_AUDIT_DIR):
        self.log_dir = Path(log_dir)
        self.log_file = self.log_dir / "security_audit.jsonl"

    @staticmethod
    def _timestamp() -> str:
        """Return a timezone-aware ISO 8601 timestamp."""
        return datetime.now(timezone.utc).astimezone().isoformat(
            timespec="milliseconds"
        )

    def record_event(
        self,
        event_type: str,
        description: str,
        outcome: str,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Validate and persist a security audit event."""

        if event_type not in self.VALID_EVENTS:
            raise ValueError("Unsupported security audit event type.")

        if not isinstance(description, str) or not description.strip():
            raise ValueError("A valid event description is required.")

        if outcome not in {"FAILED", "DENIED"}:
            raise ValueError("Invalid security event outcome.")

        # Only explicitly approved, non-sensitive context is recorded.
        safe_context = {}
        allowed_fields = {"user_id", "action", "resource", "source"}

        if context:
            safe_context = {
                key: value
                for key, value in context.items()
                if key in allowed_fields
            }

        record = {
            "timestamp": self._timestamp(),
            "event_type": event_type,
            "description": description,
            "outcome": outcome,
            "context": safe_context,
        }

        self.log_dir.mkdir(parents=True, exist_ok=True)

        with self.log_file.open("a", encoding="utf-8") as file:
            file.write(json.dumps(record, ensure_ascii=False) + "\n")

        return record
