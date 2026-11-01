"""TC-LOG-01 (TMS-F-020): events contain timestamp, type, context."""
from simulation.events import EventLogger


def test_log_has_required_fields():
    log = EventLogger()
    e = log.log("SIGNAL", {"phase": "NS_GREEN"})
    assert "timestamp" in e and "type" in e and "context" in e
    assert e["type"] == "SIGNAL"


def test_error_and_jsonl_roundtrip(tmp_path):
    log = EventLogger()
    log.log("SPAWN", {"n": 1})
    log.error("boom", {"where": "test"})
    assert len(log) == 2
    p = tmp_path / "events.jsonl"
    log.save_jsonl(p)
    back = EventLogger.load_jsonl(p)
    assert len(back) == 2
    assert back.events[1]["type"] == "ERROR"
