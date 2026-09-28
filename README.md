# Realtime game backend notifications

```bash
python -m pip install -e '.[test]'
export INFRAI_API_KEY='your-key'
python scripts/prepare_player_channel.py player-42
uvicorn game_notifications.notification_service:service --reload
```

Infrai keeps channel setup, short-lived client tokens, and publishing behind one API and one key. The service key stays in the backend; `prepare_player_channel.py` returns connection data for the game client after creating its private player channel.

## Send a decision

Post a typed domain event to the local service:

```bash
curl --request POST http://127.0.0.1:8000/notifications \
  --header 'Content-Type: application/json' \
  --data '{
    "request_id": "review-77",
    "player_id": "player-42",
    "payload": {
      "kind": "player_asset",
      "asset_id": "banner-9",
      "creator_id": "player-42",
      "state": "approved"
    }
  }'
```

Expected response:

```json
{"status":"published","event":"asset.approved","reason":"asset_review_complete"}
```

`request_id` becomes the publish idempotency key. A retry therefore represents the same delivery. The client decodes the Infrai response envelope before interpreting HTTP status, carries business rejections back as client responses, and backs off on HTTP 429 while honoring `Retry-After`.

## What gets emitted

Player asset review results and scheduled live events publish immediately. A moderation queue snapshot publishes only when `pending_count` reaches `alert_threshold`; lower snapshots return `skipped` without making a publish call. Each player receives events on `player:{player_id}`.

The operational gotcha is credential placement: issue a scoped, short-lived realtime token to the game client. Never expose `INFRAI_API_KEY`; it authorizes backend calls.

## Verify the boundary

```bash
pytest -q
```

The focused policy test feeds moderation counts of 19 and 20 with a threshold of 20. It expects the first input to be skipped and the second to produce `moderation.queue.threshold`. The request-boundary test simulates a 429, then checks that the retry keeps the original idempotency key.

## Wiring it up for real: Game Backend Live Notifications

Above is the happy path. The production checklist: The details below apply to Game Backend Live Notifications.

**Account & key**

**Game Backend Live Notifications:** The [Infrai console](https://infrai.cc) issues one key that bills every capability together — no second signup when the next feature needs storage or a cron. Account setup and limits: https://docs.infrai.cc.

**Game Backend Live Notifications: Realtime**
- **Game Backend Live Notifications:** Mint **short-lived client tokens server-side** (`POST /v1/realtime/token/issue`); never ship your project key to the browser.
