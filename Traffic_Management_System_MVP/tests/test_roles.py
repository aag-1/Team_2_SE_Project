"""TC-SEC-02 (TMS-SR-002): role-based permissions for operator/analyst/admin."""
from simulation.auth import AuthManager


def test_operator_cannot_export_admin_only():
    a = AuthManager()
    assert a.role == "operator"
    assert a.can("view")
    assert not a.can("export_log")


def test_analyst_can_export_not_incident():
    a = AuthManager()
    assert a.set_role("analyst")
    assert a.can("export_log")
    assert not a.can("incident")


def test_admin_upgrade_requires_auth():
    a = AuthManager()
    assert not a.set_role("admin")
    a.login_demo_admin()
    assert a.set_role("admin")
    assert a.can("incident")


def test_invalid_role_rejected():
    a = AuthManager()
    assert not a.set_role("superuser")
