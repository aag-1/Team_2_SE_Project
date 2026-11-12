"""Authentication and Role-Based Permissions for TMS-SR-001 & TMS-SR-002."""
from __future__ import annotations

class AccessControlManager:
    def __init__(self):
        self.users = {
            "admin": {"role": "administrator", "token": "admin_secure_token_123"},
            "analyst": {"role": "analyst", "token": "analyst_token_456"},
            "operator": {"role": "operator", "token": "operator_token_789"}
        }

    def authenticate(self, username: str, token: str) -> bool:
        """TMS-SR-001: Authenticate protected administrative changes."""
        user = self.users.get(username)
        if user and user["token"] == token:
            return True
        return False

    def authorize_action(self, role: str, action_type: str) -> bool:
        """TMS-SR-002: Enforce role-based permissions for operator, analyst, and admin."""
        permissions = {
            "administrator": ["config_change", "view_logs", "manage_users", "simulate_incidents", "reset_sim"],
            "analyst": ["view_logs", "view_kpis", "export_reports"],
            "operator": ["view_dashboard", "pause_resume", "simulate_incidents"]
        }
        allowed_actions = permissions.get(role, [])
        return action_type in allowed_actions