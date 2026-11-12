
"""Security regression tests for TMS-SR-004 (TC-SEC-04)."""

import logging
from io import BytesIO
from urllib.error import HTTPError, URLError

import pytest

from simulation.secure_api import SecureAPIClient, SecureAPIError


SECRET = "super-secret-test-token-12345"


def make_client():
    return SecureAPIClient(
        "https://example.com",
        token=SECRET,
    )


def test_http_error_does_not_expose_credentials(monkeypatch):
    def fake_urlopen(*args, **kwargs):
        raise HTTPError(
            "https://example.com/data",
            401,
            f"Unauthorized: {SECRET}",
            {},
            BytesIO(b""),
        )

    monkeypatch.setattr(
        "simulation.secure_api.urlopen",
        fake_urlopen,
    )

    with pytest.raises(SecureAPIError) as captured:
        make_client().get("data")

    assert SECRET not in str(captured.value)
    assert "401" in str(captured.value)


def test_connection_error_does_not_expose_credentials(monkeypatch):
    def fake_urlopen(*args, **kwargs):
        raise URLError(f"Connection failed with token {SECRET}")

    monkeypatch.setattr(
        "simulation.secure_api.urlopen",
        fake_urlopen,
    )

    with pytest.raises(SecureAPIError) as captured:
        make_client().get("data")

    assert SECRET not in str(captured.value)


def test_invalid_response_does_not_expose_credentials(monkeypatch):
    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            return f"invalid JSON containing {SECRET}".encode()

    monkeypatch.setattr(
        "simulation.secure_api.urlopen",
        lambda *args, **kwargs: FakeResponse(),
    )

    with pytest.raises(SecureAPIError) as captured:
        make_client().get("data")

    assert SECRET not in str(captured.value)


def test_normal_logs_do_not_contain_credentials(monkeypatch, caplog):
    def fake_urlopen(*args, **kwargs):
        raise URLError(f"Connection failed with token {SECRET}")

    monkeypatch.setattr(
        "simulation.secure_api.urlopen",
        fake_urlopen,
    )

    with caplog.at_level(logging.DEBUG):
        with pytest.raises(SecureAPIError):
            make_client().get("data")

    assert SECRET not in caplog.text
