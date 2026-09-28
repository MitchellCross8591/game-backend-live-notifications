from game_notifications.notification_policy import NotificationRequest, decide_notification


def test_moderation_queue_publishes_only_at_threshold() -> None:
    quiet = NotificationRequest.model_validate(
        {
            "request_id": "queue-snapshot-40",
            "player_id": "moderator-7",
            "payload": {
                "kind": "moderation_queue",
                "queue_name": "ugc-review",
                "pending_count": 19,
                "alert_threshold": 20,
            },
        }
    )
    alert = quiet.model_copy(
        update={"payload": quiet.payload.model_copy(update={"pending_count": 20})}
    )

    assert decide_notification(quiet).should_publish is False
    decision = decide_notification(alert)
    assert decision.should_publish is True
    assert decision.event == "moderation.queue.threshold"
    assert decision.data == {"queue_name": "ugc-review", "pending_count": 20}

