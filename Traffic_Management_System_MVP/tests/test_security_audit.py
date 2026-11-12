
"""Tests for TMS-SR-005 security audit logging (TC-SEC-05)."""

import json
from datetime import datetime

import pytest

from simulation.security_audit import SecurityAuditLogger


def test_failed_authentication_is_recorded(tmp_path):
    logger = SecurityAuditLogger(tmp_path)

    record = logger.record_event(
        "AUTHENTICATION_FAILED",
        "Authentication attempt failed",
        "FAILED",
        {"user_id": "user-101"},
    )

    assert record["event_type"] == "AUTHENTICATION_FAILED"
    assert record["outcome"] == "FAILED"
    assert record["context"]["user_id"] == "user-101"
    assert logger.log_file.exists()


def test_denied_admin_action_is_recorded(tmp_path):
    logger = SecurityAuditLogger(tmp_path)

    record = logger.record_event(
        "ADMIN_ACTION_DENIED",
        "Administrative action was denied",
        "DENIED",
        {
            "user_id": "user-101",
            "action": "RESET_SIMULATION",
            "resource": "simulation",
        },
    )

    assert record["event_type"] == "ADMIN_ACTION_DENIED"
    assert record["outcome"] == "DENIED"
    assert record["context"]["action"] == "RESET_SIMULATION"


def test_audit_records_are_valid_json_lines(tmp_path):
    logger = SecurityAuditLogger(tmp_path)

    logger.record_event(
        "AUTHENTICATION_FAILED",
        "Invalid credentials",
        "FAILED",
    )
    logger.record_event(
        "ADMIN_ACTION_DENIED",
        "Permission denied",
        "DENIED",
    )

    lines = logger.log_file.read_text(encoding="utf-8").splitlines()

    assert len(lines) == 2

    records = [json.loads(line) for line in lines]

    assert records[0]["event_type"] == "AUTHENTICATION_FAILED"
    assert records[1]["event_type"] == "ADMIN_ACTION_DENIED"


def test_audit_timestamp_is_timezone_aware(tmp_path):
    logger = SecurityAuditLogger(tmp_path)

    record = logger.record_event(
        "AUTHENTICATION_FAILED",
        "Authentication failed",
        "FAILED",
    )

    timestamp = datetime.fromisoformat(record["timestamp"])

    assert timestamp.tzinfo is not None
    assert timestamp.utcoffset() is not None


def test_sensitive_context_fields_are_not_recorded(tmp_path):
    logger = SecurityAuditLogger(tmp_path)

    secret = "do-not-log-this-token"

    logger.record_event(
        "AUTHENTICATION_FAILED",
        "Authentication failed",
        "FAILED",
        {
            "user_id": "user-101",
            "password": secret,
            "token": secret,
            "authorization": secret,
            "action": "LOGIN",
        },
    )

    contents = logger.log_file.read_text(encoding="utf-8")

    assert secret not in contents
    assert "password" not in contents
    assert "token" not in contents
    assert "authorization" not in contents


def test_unsupported_security_event_is_rejected(tmp_path):
    logger = SecurityAuditLogger(tmp_path)

    with pytest.raises(ValueError, match="Unsupported"):
        logger.record_event(
            "NORMAL_SIMULATION_EVENT",
            "Simulation started",
            "FAILED",
        )


def test_invalid_outcome_is_rejected(tmp_path):
    logger = SecurityAuditLogger(tmp_path)

    with pytest.raises(ValueError, match="outcome"):
        logger.record_event(
            "AUTHENTICATION_FAILED",
            "Authentication failed",
            "SUCCESS",
        )


def test_empty_description_is_rejected(tmp_path):
    logger = SecurityAuditLogger(tmp_path)

    with pytest.raises(ValueError, match="description"):
        logger.record_event(
            "AUTHENTICATION_FAILED",
            "",
            "FAILED",
        )
