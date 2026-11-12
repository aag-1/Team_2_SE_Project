"""Sprint 2 Unit Tests for Aditya Sehal (PES2UG24CS035)."""
import pytest
from simulation.engine import SimulationEngine
from simulation.auth_permissions import AccessControlManager
from simulation.scenario import create_scenario

def test_tc_inc_01_simulate_traffic_incidents(default_scenario):
    """TC-INC-01 (TMS-F-014): Verify traffic incident simulation."""
    engine = SimulationEngine(default_scenario)
    incident = engine.trigger_incident("R-N", "blocked_lane")
    assert incident["active"] is True
    assert incident["road_id"] == "R-N"
    assert len(engine.incidents) == 1
    engine.reset()
    assert len(engine.incidents) == 0


def test_tc_nf_04_state_consistency_across_cycles(default_scenario):
    """TC-NF-04 (TMS-NF-004): State remains valid across 20+ control cycles."""
    engine = SimulationEngine(default_scenario)
    engine.start = lambda: setattr(engine, 'state', 'RUNNING')
    engine.resume()
    
    for _ in range(25):
        engine.tick(1/30)
        
    assert engine.tick_count == 25
    assert engine.clock > 0
    
    # Test pause/resume state validity
    engine.pause()
    ticks_at_pause = engine.tick_count
    engine.tick(1/30)
    assert engine.tick_count == ticks_at_pause  # Should not advance while paused


def test_tc_sec_01_admin_authentication():
    """TC-SEC-01 (TMS-SR-001): Require authentication before admin configuration changes."""
    acm = AccessControlManager()
    assert acm.authenticate("admin", "wrong_token") is False
    assert acm.authenticate("admin", "admin_secure_token_123") is True


def test_tc_sec_02_role_based_permissions():
    """TC-SEC-02 (TMS-SR-002): Enforce role-based permissions for operator/analyst/admin."""
    acm = AccessControlManager()
    # Operators cannot perform admin config changes
    assert acm.authorize_action("operator", "config_change") is False
    # Administrators are permitted
    assert acm.authorize_action("administrator", "config_change") is True
    # Analysts can view logs
    assert acm.authorize_action("analyst", "view_logs") is True