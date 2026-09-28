import httpx

from game_notifications.infrai_realtime import RealtimeClient


def test_publish_retries_429_with_same_idempotency_key() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if len(requests) == 1:
            return httpx.Response(
                429,
                headers={"Retry-After": "0"},
                json={"ok": False, "data": None, "error": {"code": "RATE_LIMITED"}, "metadata": {}},
            )
        return httpx.Response(
            200,
            json={"ok": True, "data": {"published": True}, "error": None, "metadata": {}},
        )

    client = RealtimeClient(
        "test-key",
        transport=httpx.MockTransport(handler),
        sleep=lambda _: None,
    )
    try:
        result = client.publish(
            channel="player:42",
            event="asset.approved",
            data={"asset_id": "asset-9"},
            account_id="42",
            idempotency_key="review-77",
        )
    finally:
        client.close()

    assert result == {"published": True}
    assert len(requests) == 2
    assert requests[0].headers["Idempotency-Key"] == "review-77"
    assert requests[1].headers["Idempotency-Key"] == "review-77"

