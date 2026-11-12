
"""Secure optional client for external traffic sensor/API communication."""

import json
import os
import ssl
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen


class SecureAPIError(Exception):
    """Raised when a secure external API request fails."""


class SecureAPIClient:
    """Communicates with external APIs using HTTPS and bearer authentication."""

    def __init__(self, base_url, token=None, timeout=5):
        parsed_url = urlparse(base_url)

        if parsed_url.scheme != "https":
            raise ValueError("External API connections must use HTTPS.")

        if not parsed_url.netloc:
            raise ValueError("A valid API URL is required.")

        self.base_url = base_url.rstrip("/")
        self.token = token or os.getenv("TRAFFIC_API_TOKEN")
        self.timeout = timeout

        if not self.token:
            raise ValueError(
                "API token missing. Set the TRAFFIC_API_TOKEN environment variable."
            )

    def get(self, endpoint):
        """Send an authenticated HTTPS GET request and return JSON data."""
        if not endpoint or endpoint.startswith("//"):
            raise ValueError("A valid API endpoint is required.")

        parsed_endpoint = urlparse(endpoint)

        if parsed_endpoint.scheme or parsed_endpoint.netloc:
            raise ValueError("Use a relative API endpoint, not another URL.")

        url = f"{self.base_url}/{endpoint.lstrip('/')}"

        request = Request(
            url,
            headers={
                "Authorization": f"Bearer {self.token}",
                "Accept": "application/json",
            },
            method="GET",
        )

        try:
            # Default SSL context verifies the server certificate.
            context = ssl.create_default_context()

            with urlopen(
                request,
                timeout=self.timeout,
                context=context,
            ) as response:
                return json.loads(response.read().decode("utf-8"))

        except HTTPError as exc:
            raise SecureAPIError(
                f"API request failed with HTTP status {exc.code}."
            ) from None

        except URLError:
            raise SecureAPIError(
                "Unable to connect securely to the external API."
            ) from None

        except (TimeoutError, json.JSONDecodeError, UnicodeDecodeError):
            raise SecureAPIError(
                "API request failed due to a timeout or invalid response."
            ) from None
