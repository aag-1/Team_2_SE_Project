"""TC-SEC-03 (TMS-SR-003): malformed imported data is rejected without a crash."""
import json
import random

import pytest

from simulation.scenario import (MAX_FILE_BYTES, ScenarioError, load_scenario,
                                 validate_scenario)

MALFORMED_FILES = {
    "empty": b"",
    "not_json": b"hello world",
    "truncated": b'{"window": {"width": 1100',
    "top_level_list": b"[1, 2, 3]",
    "nan": b'{"window": {"width": NaN, "height": 760}, "simulation": {}}',
    "infinity": b'{"window": {"width": Infinity, "height": 760}, "simulation": {}}',
    "duplicate_keys": b'{"window": {"width": 1100, "width": 9999, "height": 760}, "simulation": {}}',
    "not_utf8": b"\xff\xfe\x00\x00\x81\x82",
    "deep_nesting": b"[" * 100_000 + b"]" * 100_000,
    "null": b"null",
}


@pytest.mark.parametrize("name", sorted(MALFORMED_FILES))
def test_malformed_files_rejected_cleanly(tmp_path, name):
    path = tmp_path / f"{name}.json"
    path.write_bytes(MALFORMED_FILES[name])
    with pytest.raises(ScenarioError):
        load_scenario(path)


def test_oversized_file_rejected_before_parsing(tmp_path):
    path = tmp_path / "big.json"
    path.write_bytes(b" " * (MAX_FILE_BYTES + 1))
    with pytest.raises(ScenarioError, match="limit"):
        load_scenario(path)


def test_missing_file_and_directory_rejected(tmp_path):
    with pytest.raises(ScenarioError):
        load_scenario(tmp_path / "nope.json")
    with pytest.raises(ScenarioError):
        load_scenario(tmp_path)


@pytest.mark.parametrize("mutate,expected", [
    (lambda d: d.update(extra_field=1), "unknown field"),
    (lambda d: d["simulation"].update(eval_me="__import__('os')"), "unknown field"),
    (lambda d: d.update(name="../../etc/passwd"), "name"),
    (lambda d: d.update(name="<script>alert(1)</script>"), "name"),
    (lambda d: d["window"].update(title="bad\x00title\x1b[31m"), "window.title"),
    (lambda d: d["network"]["roads"][0].update(id="R N; DROP TABLE"), "id"),
    (lambda d: d.update(schema_version=99), "schema_version"),
    (lambda d: d.update(simulation="all of it"), "'simulation' must be an object"),
    (lambda d: d["network"].update(roads=[{"id": "R"}] * 50), "at most 4 roads"),
])
def test_hostile_or_wrong_fields_rejected(raw_default, mutate, expected):
    mutate(raw_default)
    with pytest.raises(ScenarioError) as exc:
        validate_scenario(raw_default)
    assert expected in str(exc.value)


def test_whitespace_in_names_is_sanitized(raw_default):
    raw_default["name"] = "   Peak    hour  "
    assert validate_scenario(raw_default).name == "Peak hour"


def test_random_corruption_never_crashes(tmp_path, raw_default):
    """Light fuzz: 500 randomly corrupted copies of a valid file."""
    original = json.dumps(raw_default).encode()
    rng = random.Random(2026)
    path = tmp_path / "fuzz.json"
    for _ in range(500):
        data = bytearray(original)
        for _ in range(rng.randint(1, 8)):
            data[rng.randrange(len(data))] = rng.randrange(256)
        path.write_bytes(bytes(data))
        try:
            load_scenario(path)
        except ScenarioError:
            pass  # rejected cleanly; any other exception fails the test
