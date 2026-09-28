from __future__ import annotations

import os
from contextlib import asynccontextmanager
from typing import Iterator, Literal

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel

from .infrai_realtime import InfraiError, InfraiTransportError, RealtimeClient
from .notification_policy import NotificationRequest, decide_notification


class DeliveryResult(BaseModel):
    status: Literal["published", "skipped"]
    event: str
    reason: str


def realtime_client() -> Iterator[RealtimeClient]:
    api_key = os.environ.get("INFRAI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=503, detail="INFRAI_API_KEY is required")
    client = RealtimeClient(api_key)
    try:
        yield client
    finally:
        client.close()


@asynccontextmanager
async def lifespan(_: FastAPI):
    yield


service = FastAPI(title="Game notification relay", lifespan=lifespan)


@service.post("/notifications", response_model=DeliveryResult)
def send_notification(
    request: NotificationRequest,
    client: RealtimeClient = Depends(realtime_client),
) -> DeliveryResult:
    decision = decide_notification(request)
    if not decision.should_publish:
        return DeliveryResult(status="skipped", event=decision.event, reason=decision.reason)

    try:
        client.publish(
            channel=f"player:{request.player_id}",
            event=decision.event,
            data=decision.data,
            account_id=request.player_id,
            idempotency_key=request.request_id,
        )
    except InfraiError as exc:
        client_status = exc.status_code if 400 <= exc.status_code < 500 else 502
        raise HTTPException(status_code=client_status, detail={"code": exc.code, "message": str(exc)}) from exc
    except InfraiTransportError as exc:
        raise HTTPException(status_code=502, detail="Notification transport failed") from exc

    return DeliveryResult(status="published", event=decision.event, reason=decision.reason)

