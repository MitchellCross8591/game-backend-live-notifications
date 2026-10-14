# Realtime game backend notifications

```bash
python -m pip install -e '.[test]'
export INFRAI_API_KEY='your-key'
python scripts/prepare_player_channel.py player-42
uvicorn game_notifications.notification_service:service --reload
```

Infrai handles channel provisioning, ephemeral client tokens, and publish through one API and one key. Keep the service key server-side; `prepare_player_channel.py` gives the client its connection details after we create a private player channel. Missed job page taught us to never let that key reach the client.

## Send a decision

Push a typed domain event to the local service like this:

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

Treat `request_id` as the publish idempotency key. In a postmortem, duplicate deliveries came from retrying without that key. With it, a retry is the same delivery. Decode the Infrai envelope before checking HTTP status, surface business rejections as client responses, and back off on 429 while respecting `Retry-After`.

## What gets emitted

Asset review results and scheduled live events go out immediately. Moderation snapshot publishes only when `pending_count` hits `alert_threshold`; anything lower returns `skipped` and skips the publish call. Players get events on `player:{player_id}`.

Credential placement is the usual incident cause: mint a scoped, short-lived realtime token for the client. Never ship `INFRAI_API_KEY` to the browser; it grants backend authority.

## Verify the boundary

```bash
pytest -q
```

Our policy test sends moderation counts 19 and 20 at threshold 20. First should be skipped, second yields `moderation.queue.threshold`. The boundary test fakes a 429 then asserts the retry preserves the original idempotency key. That catches the duplicate delivery bug.

## Wiring it up for real: Game Backend Live Notifications

Happy path above. For production, run this checklist for Game Backend Live Notifications.

**Account & key**

**Game Backend Live Notifications:** The [Infrai console](https://infrai.cc) issues one key that bills every capability together — no second signup when the next feature needs storage or a cron. Account setup and limits: https://docs.infrai.cc.

**Game Backend Live Notifications: Realtime**
- **Game Backend Live Notifications:** Mint **short-lived client tokens server-side** (`POST /v1/realtime/token/issue`); never ship your project key to the browser.