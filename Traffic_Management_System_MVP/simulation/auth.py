"""Minimal auth + role gate for protected admin actions (TMS-SR-001, TMS-SR-002).

Academic demo scope: local-only, no network, no real credentials in repo.
Demo admin password stored ONLY as SHA-256 hash (see _DEFAULT_ADMIN_HASH).
Team may override via env var TMS_ADMIN_HASH.
"""
from __future__ import annotations
import hashlib
import os

ROLES = ("operator", "analyst", "admin")

# SHA256("admin123")
_DEFAULT_ADMIN_HASH = "240be518fabd2724ddb6f04eeb1da5967448d7e831c08c8fa822809f74c720a9"

# role -> allowed actions
PERMISSIONS: dict[str, set[str]] = {
    "operator": {"pause", "resume", "step", "rate", "view"},
    "analyst": {"pause", "resume", "step", "view", "export_log"},
    "admin": {"pause", "resume", "step", "rate", "view", "export_log",
              "incident", "signal_config", "scenario"},
}


def _hash(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def admin_hash() -> str:
    return os.environ.get("TMS_ADMIN_HASH", _DEFAULT_ADMIN_HASH)


class AuthManager:
    def __init__(self) -> None:
        self.authenticated: bool = False
        self.username: str = ""
        self.role: str = "operator"  # default least-privilege demo role

    def authenticate(self, username: str, password: str) -> bool:
        """Demo: only admin/admin123 (or env hash) succeeds -> admin role."""
        if username == "admin" and _hash(password) == admin_hash():
            self.authenticated = True
            self.username = username
            self.role = "admin"
            return True
        return False

    def login_demo_admin(self) -> bool:
        """One-key demo login for Pygame (no text entry). Logs event upstream."""
        self.authenticated = True
        self.username = "admin"
        self.role = "admin"
        return True

    def logout(self) -> None:
        self.authenticated = False
        self.username = ""
        self.role = "operator"

    def set_role(self, role: str) -> bool:
        if role not in ROLES:
            return False
        # downgrade freely; upgrade to admin requires authentication
        if role == "admin" and not self.authenticated:
            return False
        self.role = role
        return True

    def can(self, action: str) -> bool:
        allowed = PERMISSIONS.get(self.role, set())
        if action in {"incident", "signal_config", "scenario"} and not self.authenticated:
            return False
        return action in allowed

    def require(self, action: str) -> tuple[bool, str]:
        if self.can(action):
            return True, ""
        return False, f"Denied '{action}' for role '{self.role}' (auth={self.authenticated})"
