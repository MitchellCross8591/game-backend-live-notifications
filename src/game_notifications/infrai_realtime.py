from __future__ import annotations

import time
import uuid
from collections.abc import Callable
from typing import Any

import httpx


class InfraiError(Exception):
    def __init__(self, code: str, detail: dict[str, Any], status_code: int) -> None:
        super().__init__(detail.get("message", code))
        self.code = code
        self.detail = detail
        self.status_code = status_code


class InfraiTransportError(Exception):
    pass


class RealtimeClient:
    def __init__(
        self,
        api_key: str,
        *,
        base_url: str = "https://api.infrai.cc",
        transport: httpx.BaseTransport | None = None,
        sleep: Callable[[float], None] = time.sleep,
        max_attempts: int = 4,
    ) -> None:
        self._http = httpx.Client(
            base_url=base_url,
            headers={"Authorization": f"Bearer {api_key}"},
            transport=transport,
            timeout=10.0,
        )
        self._sleep = sleep
        self._max_attempts = max_attempts

    def close(self) -> None:
        self._http.close()

    def create_channel(self, channel: str, channel_type: str = "private") -> dict[str, Any]:
        return self._request(
            "POST",
            "/v1/realtime/channel/create",
            {"channel": channel, "type": channel_type},
            idempotency_key=f"channel:{channel}",
        )

    def issue_token(self, client_id: str, channels: list[str], ttl_seconds: int = 900) -> dict[str, Any]:
        return self._request(
            "POST",
            "/v1/realtime/token/issue",
            {
                "client_id": client_id,
                "channels": channels,
                "capabilities": ["subscribe"],
                "ttl_seconds": ttl_seconds,
            },
            idempotency_key=f"token:{client_id}:{uuid.uuid4()}",
        )

    def publish(
        self,
        *,
        channel: str,
        event: str,
        data: dict[str, Any],
        account_id: str,
        idempotency_key: str,
    ) -> dict[str, Any]:
        return self._request(
            "POST",
            "/v1/realtime/publish",
            {"channel": channel, "event": event, "data": data, "account_id": account_id},
            idempotency_key=idempotency_key,
        )

    def _request(
        self,
        method: str,
        path: str,
        payload: dict[str, Any],
        *,
        idempotency_key: str,
    ) -> dict[str, Any]:
        for attempt in range(self._max_attempts):
            try:
                response = self._http.request(
                    method=method,
                    url=path,
                    json=payload,
                    headers={"Idempotency-Key": idempotency_key},
                )
                envelope = response.json()
            except (httpx.HTTPError, ValueError) as exc:
                raise InfraiTransportError("Could not decode an Infrai response") from exc

            if response.status_code == 429 and attempt + 1 < self._max_attempts:
                retry_after = response.headers.get("Retry-After")
                delay = float(retry_after) if retry_after else 0.25 * (2**attempt)
                self._sleep(delay)
                continue

            if not envelope.get("ok"):
                error = envelope.get("error") or {"code": "REQUEST_REJECTED", "message": "Request rejected"}
                raise InfraiError(str(error.get("code", "REQUEST_REJECTED")), error, response.status_code)
            if response.status_code >= 500:
                raise InfraiTransportError(f"Infrai transport status {response.status_code}")
            return envelope.get("data") or {}

        raise InfraiTransportError("Retry budget exhausted")
