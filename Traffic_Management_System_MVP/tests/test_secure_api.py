
import json
import ssl
from io import BytesIO
from urllib.error import HTTPError

import pytest

from simulation.secure_api import SecureAPIClient, SecureAPIError


class FakeResponse:
    def __init__(self, data):
        self.data = data

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def read(self):
        return self.data


def test_client_rejects_http_url():
    with pytest.raises(ValueError, match="HTTPS"):
        SecureAPIClient("http://example.com", token="test-token")


def test_client_requires_token(monkeypatch):
    monkeypatch.delenv("TRAFFIC_API_TOKEN", raising=False)

    with pytest.raises(ValueError, match="token missing"):
        SecureAPIClient("https://example.com")


def test_client_reads_token_from_environment(monkeypatch):
    monkeypatch.setenv("TRAFFIC_API_TOKEN", "environment-token")

    client = SecureAPIClient("https://example.com")

    assert client.token == "environment-token"


def test_get_uses_bearer_authentication_and_verified_https(
    monkeypatch,
):
    captured = {}

    def fake_urlopen(request, timeout, context):
        captured["request"] = request
        captured["timeout"] = timeout
        captured["context"] = context

        return FakeResponse(
            json.dumps({"vehicles": 25}).encode("utf-8")
        )

    monkeypatch.setattr(
        "simulation.secure_api.urlopen",
        fake_urlopen,
    )

    client = SecureAPIClient(
        "https://example.com",
        token="test-token",
        timeout=8,
    )

    result = client.get("/sensors/data")

    assert result == {"vehicles": 25}
    assert captured["request"].full_url == (
        "https://example.com/sensors/data"
    )
    assert captured["request"].get_header("Authorization") == (
        "Bearer test-token"
    )
    assert captured["timeout"] == 8
    assert isinstance(captured["context"], ssl.SSLContext)
    assert captured["context"].verify_mode == ssl.CERT_REQUIRED
    assert captured["context"].check_hostname is True


def test_get_rejects_absolute_endpoint():
    client = SecureAPIClient(
        "https://example.com",
        token="test-token",
    )

    with pytest.raises(ValueError, match="relative API endpoint"):
        client.get("http://other-example.com/data")


def test_get_handles_http_errors(monkeypatch):
    def fake_urlopen(*args, **kwargs):
        raise HTTPError(
            "https://example.com/data",
            401,
            "Unauthorized",
            {},
            BytesIO(b""),
        )

    monkeypatch.setattr(
        "simulation.secure_api.urlopen",
        fake_urlopen,
    )

    client = SecureAPIClient(
        "https://example.com",
        token="test-token",
    )

    with pytest.raises(SecureAPIError, match="401"):
        client.get("data")


def test_get_handles_invalid_json(monkeypatch):
    def fake_urlopen(*args, **kwargs):
        return FakeResponse(b"not valid json")

    monkeypatch.setattr(
        "simulation.secure_api.urlopen",
        fake_urlopen,
    )

    client = SecureAPIClient(
        "https://example.com",
        token="test-token",
    )

    with pytest.raises(SecureAPIError, match="API request failed"):
        client.get("data")
