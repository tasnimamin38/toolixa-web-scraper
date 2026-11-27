"""HTTP client for any provider exposing the OpenAI Chat Completions API shape."""

from __future__ import annotations

from typing import Any

import httpx

from toolixa_core.gateway.store import ProviderRecord


class ProviderHTTPError(RuntimeError):
    def __init__(self, message: str, *, status_code: int = 502) -> None:
        super().__init__(message)
        self.status_code = status_code


class ProviderHTTPClient:
    """Small, protocol-focused adapter with testable HTTP transport injection."""

    def __init__(
        self, *, transport: httpx.AsyncBaseTransport | None = None, timeout: float = 45.0
    ) -> None:
        self.transport = transport
        self.timeout = timeout

    def _headers(self, api_key: str) -> dict[str, str]:
        headers = {"Accept": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        return headers

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            timeout=httpx.Timeout(self.timeout, connect=min(self.timeout, 10.0)),
            follow_redirects=False,
            trust_env=False,
            transport=self.transport,
        )

    @staticmethod
    def _url(provider: ProviderRecord, suffix: str) -> str:
        return f"{provider.base_url.rstrip('/')}/{suffix.lstrip('/')}"

    @staticmethod
    def error_message(response: httpx.Response, api_key: str = "") -> str:
        message = f"upstream provider returned HTTP {response.status_code}"
        try:
            body = response.json()
            error = body.get("error", body) if isinstance(body, dict) else body
            if isinstance(error, dict):
                candidate = error.get("message") or error.get("detail")
            else:
                candidate = str(error)
            if candidate:
                message = str(candidate)[:300]
        except (ValueError, TypeError):
            pass
        if api_key:
            message = message.replace(api_key, "[REDACTED]")
        return message

    @staticmethod
    def _redact_payload(value: Any, api_key: str) -> Any:
        if not api_key:
            return value
        if isinstance(value, str):
            return value.replace(api_key, "[REDACTED]")
        if isinstance(value, list):
            return [ProviderHTTPClient._redact_payload(item, api_key) for item in value]
        if isinstance(value, dict):
            return {
                key: ProviderHTTPClient._redact_payload(item, api_key)
                for key, item in value.items()
            }
        return value

    async def list_models(self, provider: ProviderRecord, api_key: str) -> list[str]:
        try:
            async with self._client() as client:
                response = await client.get(
                    self._url(provider, "models"), headers=self._headers(api_key)
                )
        except httpx.HTTPError as exc:
            raise ProviderHTTPError(f"could not reach provider: {type(exc).__name__}") from exc
        if response.is_error:
            raise ProviderHTTPError(
                self.error_message(response, api_key), status_code=response.status_code
            )
        try:
            payload = response.json()
        except ValueError as exc:
            raise ProviderHTTPError("provider returned an invalid model-list response") from exc
        data = payload.get("data") if isinstance(payload, dict) else None
        if not isinstance(data, list):
            raise ProviderHTTPError("provider model-list response must contain a data array")
        models = [
            item["id"].replace(api_key, "[REDACTED]") if api_key else item["id"]
            for item in data
            if isinstance(item, dict) and isinstance(item.get("id"), str)
        ]
        if len(models) > 300:
            models = models[:300]
        return list(dict.fromkeys(models))

    async def chat_completion(
        self, provider: ProviderRecord, api_key: str, upstream_model: str, payload: dict[str, Any]
    ) -> dict[str, Any]:
        request_payload = dict(payload)
        request_payload["model"] = upstream_model
        try:
            async with self._client() as client:
                response = await client.post(
                    self._url(provider, "chat/completions"),
                    headers=self._headers(api_key),
                    json=request_payload,
                )
        except httpx.HTTPError as exc:
            raise ProviderHTTPError(f"could not reach provider: {type(exc).__name__}") from exc
        if response.is_error:
            raise ProviderHTTPError(
                self.error_message(response, api_key), status_code=response.status_code
            )
        try:
            result = response.json()
        except ValueError as exc:
            raise ProviderHTTPError(
                "provider returned an invalid chat-completion response"
            ) from exc
        if not isinstance(result, dict):
            raise ProviderHTTPError("provider chat-completion response must be a JSON object")
        return self._redact_payload(result, api_key)

    async def open_stream(
        self, provider: ProviderRecord, api_key: str, upstream_model: str, payload: dict[str, Any]
    ) -> tuple[httpx.AsyncClient, httpx.Response]:
        request_payload = dict(payload)
        request_payload["model"] = upstream_model
        request_payload["stream"] = True
        client = self._client()
        try:
            request = client.build_request(
                "POST",
                self._url(provider, "chat/completions"),
                headers={**self._headers(api_key), "Accept": "text/event-stream"},
                json=request_payload,
            )
            response = await client.send(request, stream=True)
            return client, response
        except httpx.HTTPError as exc:
            await client.aclose()
            raise ProviderHTTPError(f"could not reach provider: {type(exc).__name__}") from exc
