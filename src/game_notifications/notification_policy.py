from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, Field


class PlayerAsset(BaseModel):
    kind: Literal["player_asset"]
    asset_id: str
    creator_id: str
    state: Literal["approved", "rejected"]


class LiveEvent(BaseModel):
    kind: Literal["live_event"]
    event_id: str
    title: str
    starts_at: str


class ModerationQueue(BaseModel):
    kind: Literal["moderation_queue"]
    queue_name: str
    pending_count: int = Field(ge=0)
    alert_threshold: int = Field(default=20, ge=1)


NotificationPayload = Annotated[
    PlayerAsset | LiveEvent | ModerationQueue,
    Field(discriminator="kind"),
]


class NotificationRequest(BaseModel):
    request_id: str
    player_id: str
    payload: NotificationPayload


class NotificationDecision(BaseModel):
    should_publish: bool
    event: str
    data: dict[str, str | int]
    reason: str


def decide_notification(request: NotificationRequest) -> NotificationDecision:
    payload = request.payload
    if isinstance(payload, ModerationQueue):
        publish = payload.pending_count >= payload.alert_threshold
        return NotificationDecision(
            should_publish=publish,
            event="moderation.queue.threshold",
            data={"queue_name": payload.queue_name, "pending_count": payload.pending_count},
            reason="threshold_reached" if publish else "below_threshold",
        )
    if isinstance(payload, PlayerAsset):
        return NotificationDecision(
            should_publish=True,
            event=f"asset.{payload.state}",
            data={"asset_id": payload.asset_id, "creator_id": payload.creator_id},
            reason="asset_review_complete",
        )
    return NotificationDecision(
        should_publish=True,
        event="live_event.scheduled",
        data={"event_id": payload.event_id, "title": payload.title, "starts_at": payload.starts_at},
        reason="live_event_visible",
    )

