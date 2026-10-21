"""Shared optional HTTP boundary; never imported by the runtime."""

from __future__ import annotations

import asyncio
import json
import math
from collections.abc import AsyncIterator, Callable
from typing import Any
from urllib.parse import urlsplit

from ..exceptions import (
    ConfigurationError,
    ModelAuthenticationError,
    ModelRateLimitError,
    ModelResponseError,
    ModelTimeoutError,
    ModelUnavailableError,
)


def status_error(status: int) -> None:
    if status < 400:
        return
    if status in {401, 403}:
        raise ModelAuthenticationError("Provider authentication rejected")
    if status == 429:
        raise ModelRateLimitError("Provider rate limit reached", retryable=True)
    if status == 408:
        raise ModelTimeoutError("Provider request timed out", retryable=True)
    if status >= 500:
        raise ModelUnavailableError("Provider unavailable", retryable=True)
    raise ModelResponseError(f"Provider rejected request (HTTP {status})")


class HttpTransport:
    """Application-injected clients remain caller-owned. No redirects or env proxies.

    Only explicit HTTP 429/5xx responses can be retried. Ambiguous network failures
    and streams are never retried, avoiding silent duplicate generation charges.
    """

    def __init__(
        self,
        base_url: str,
        headers: dict[str, str],
        *,
        client: Any = None,
        timeout: float = 60,
        retries: int = 0,
        error_handler: Callable[[int, dict[str, Any] | None], None] | None = None,
    ) -> None:
        parts = urlsplit(base_url)
        if (
            parts.scheme not in {"https", "http"}
            or not parts.hostname
            or parts.username
            or parts.password
            or parts.query
            or parts.fragment
        ):
            raise ConfigurationError("Invalid provider base URL")
        if parts.scheme == "http" and parts.hostname not in {"localhost", "127.0.0.1", "::1"}:
            raise ConfigurationError("Plain HTTP is allowed only on loopback")
        if not math.isfinite(timeout) or timeout <= 0 or not 0 <= retries <= 3:
            raise ConfigurationError("Timeout must be finite/positive; retries must be 0..3")
        try:
            import httpx
        except ImportError:
            raise ConfigurationError("Install the selected provider extra") from None
        self.httpx = httpx
        self._owned = client is None
        self.client = client or httpx.AsyncClient(trust_env=False, follow_redirects=False)
        self.base_url = base_url.rstrip("/")
        self._headers = dict(headers)
        self.timeout = timeout
        self.retries = retries
        self.error_handler = error_handler

    def _raise_status_error(self, response: Any) -> None:
        if response.status_code < 400:
            return
        payload: dict[str, Any] | None = None
        if self.error_handler is not None:
            try:
                candidate = response.json()
                if isinstance(candidate, dict):
                    payload = candidate
            except ValueError:
                pass
            self.error_handler(response.status_code, payload)
        status_error(response.status_code)

    def _raise_body_error(self, payload: dict[str, Any]) -> None:
        if self.error_handler is not None:
            self.error_handler(200, payload)
        raise ModelResponseError("Invalid provider response")

    async def aclose(self) -> None:
        if self._owned:
            await self.client.aclose()

    async def post(self, path: str, body: dict[str, Any]) -> dict[str, Any]:
        try:
            for attempt in range(self.retries + 1):
                response = await self.client.post(
                    self.base_url + path,
                    json=body,
                    headers=self._headers,
                    timeout=self.timeout,
                    follow_redirects=False,
                )
                if (
                    response.status_code in {408, 429, 500, 502, 503, 504, 529}
                    and attempt < self.retries
                ):
                    try:
                        delay = float(response.headers.get("retry-after", 0.25 * (2**attempt)))
                    except ValueError:
                        delay = 0.25 * (2**attempt)
                    await asyncio.sleep(min(max(delay, 0), 5))
                    continue
                if 300 <= response.status_code < 400:
                    raise ModelResponseError("Provider redirect refused")
                self._raise_status_error(response)
                value = response.json()
                if not isinstance(value, dict):
                    raise ModelResponseError("Invalid provider response")
                if "error" in value:
                    self._raise_body_error(value)
                return value
        except self.httpx.TimeoutException:
            raise ModelTimeoutError("Provider request timed out", retryable=True) from None
        except self.httpx.RequestError:
            raise ModelUnavailableError("Provider transport failed", retryable=True) from None
        except ValueError:
            raise ModelResponseError("Provider returned invalid JSON") from None
        raise ModelUnavailableError("Provider attempts exhausted")  # pragma: no cover

    async def get(self, path: str) -> dict[str, Any]:
        """Fetch a provider resource with the same bounded retry policy as POST."""

        try:
            for attempt in range(self.retries + 1):
                response = await self.client.get(
                    self.base_url + path,
                    headers=self._headers,
                    timeout=self.timeout,
                    follow_redirects=False,
                )
                if (
                    response.status_code in {408, 429, 500, 502, 503, 504, 529}
                    and attempt < self.retries
                ):
                    try:
                        delay = float(response.headers.get("retry-after", 0.25 * (2**attempt)))
                    except ValueError:
                        delay = 0.25 * (2**attempt)
                    await asyncio.sleep(min(max(delay, 0), 5))
                    continue
                if 300 <= response.status_code < 400:
                    raise ModelResponseError("Provider redirect refused")
                self._raise_status_error(response)
                value = response.json()
                if not isinstance(value, dict):
                    raise ModelResponseError("Invalid provider response")
                if "error" in value:
                    self._raise_body_error(value)
                return value
        except self.httpx.TimeoutException:
            raise ModelTimeoutError("Provider request timed out", retryable=True) from None
        except self.httpx.RequestError:
            raise ModelUnavailableError("Provider transport failed", retryable=True) from None
        except ValueError:
            raise ModelResponseError("Provider returned invalid JSON") from None
        raise ModelUnavailableError("Provider attempts exhausted")  # pragma: no cover

    async def stream(
        self, path: str, body: dict[str, Any], *, ndjson: bool = False
    ) -> AsyncIterator[dict[str, Any]]:
        try:
            async with self.client.stream(
                "POST",
                self.base_url + path,
                json=body,
                headers=self._headers,
                timeout=self.timeout,
                follow_redirects=False,
            ) as response:
                if 300 <= response.status_code < 400:
                    raise ModelResponseError("Provider redirect refused")
                self._raise_status_error(response)
                data: list[str] = []
                async for line in response.aiter_lines():
                    if ndjson:
                        if line.strip():
                            yield self._decode(line)
                    elif line.startswith("data:"):
                        data.append(line[5:].lstrip())
                    elif not line and data:
                        item = "\n".join(data)
                        data = []
                        if item == "[DONE]":
                            return
                        yield self._decode(item)
                if data:
                    item = "\n".join(data)
                    if item != "[DONE]":
                        yield self._decode(item)
        except self.httpx.TimeoutException:
            raise ModelTimeoutError("Provider stream timed out") from None
        except self.httpx.RequestError:
            raise ModelUnavailableError("Provider stream interrupted") from None

    def _decode(self, text: str) -> dict[str, Any]:
        try:
            value = json.loads(text)
        except ValueError:
            raise ModelResponseError("Invalid provider stream JSON") from None
        if not isinstance(value, dict):
            raise ModelResponseError("Provider stream error")
        if "error" in value:
            self._raise_body_error(value)
        return value
