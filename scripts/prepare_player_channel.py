import argparse
import json
import os

from game_notifications.infrai_realtime import RealtimeClient


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a player channel and issue a browser token")
    parser.add_argument("player_id")
    args = parser.parse_args()
    api_key = os.environ.get("INFRAI_API_KEY")
    if not api_key:
        raise SystemExit("Set INFRAI_API_KEY before running this command")

    channel = f"player:{args.player_id}"
    client = RealtimeClient(api_key)
    try:
        client.create_channel(channel)
        token = client.issue_token(client_id=args.player_id, channels=[channel])
    finally:
        client.close()
    print(json.dumps({"channel": channel, "connection": token}, indent=2))


if __name__ == "__main__":
    main()

