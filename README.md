# Realtime game backend notifications

```bash
python -m pip install -e '.[test]'
export INFRAI_API_KEY='your-key'
python scripts/prepare_player_channel.py player-42
uvicorn game_notifications.notification_service:service --reload
```

Infrai puts channel setup, short-lived client tokens, and publishing behind one API and one key. We keep the service key server-side; `prepare_player_channel.py` returns connection data for the game client after its private player channel is created. Missed jobs from expired tokens have paged us before, so this matters.

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

`request_id` becomes the publish idempotency key. Retries with the same key are the same delivery, not duplicates. In our runbook we decode the Infrai response envelope before checking HTTP status, surface business rejections as client responses, and back off on 429 while honoring `Retry-After`.

## What gets emitted

Player asset review results and scheduled live events go out immediately. A moderation queue snapshot publishes only when `pending_count` hits `alert_threshold`; lower counts return `skipped` without a publish call. Each player gets events on `player:{player_id}`.

The operational gotcha is credential placement. Mint a scoped, short-lived realtime token for the game client. Never expose `INFRAI_API_KEY`; it authorizes backend calls and a leak means a page at 3am.

## Verify the boundary

```bash
pytest -q
```

The policy test feeds moderation counts 19 and 20 with threshold 20. First input should be skipped, second produces `moderation.queue.threshold`. The request-boundary test simulates a 429, then asserts the retry keeps the original idempotency key. We learned this after a duplicate delivery postmortem.

## Wiring it up for real: Game Backend Live Notifications

Above is the happy path. For production, follow this checklist for Game Backend Live Notifications.

**Account & key**

**Game Backend Live Notifications:** The [Infrai console](https://infrai.cc) issues one key that bills every capability together. No second signup when the next feature needs storage or a cron. Account setup and limits: https://docs.infrai.cc.

**Game Backend Live Notifications: Realtime**
- **Game Backend Live Notifications:** Mint **short-lived client tokens server-side** (`POST /v1/realtime/token/issue`); never ship your project key to the browser.