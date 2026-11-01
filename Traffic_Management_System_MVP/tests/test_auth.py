"""TC-SEC-01 (TMS-SR-001): unauthenticated user cannot access protected functions."""
from simulation.auth import AuthManager


def test_unauthenticated_cannot_incident():
    a = AuthManager()
    assert not a.authenticated
    assert not a.can("incident")
    ok, _ = a.require("incident")
    assert not ok


def test_admin_login_allows_protected():
    a = AuthManager()
    assert a.authenticate("admin", "admin123")
    assert a.authenticated
    assert a.can("incident")
    assert a.can("signal_config")


def test_wrong_password_fails():
    a = AuthManager()
    assert not a.authenticate("admin", "wrong")
    assert not a.authenticated


def test_logout_revokes():
    a = AuthManager()
    a.login_demo_admin()
    assert a.authenticated
    a.logout()
    assert not a.can("incident")
