from slack_sdk import WebClient
from config import SLACK_BOT_TOKEN


def get_slack_client() -> WebClient:
    return WebClient(token=SLACK_BOT_TOKEN)


def post_message(channel: str, text: str, thread_ts: str | None = None) -> str:
    client = get_slack_client()
    response = client.chat_postMessage(
        channel=channel,
        text=text,
        thread_ts=thread_ts,
        mrkdwn=True,
    )
    return response["ts"]


def lookup_user_id(email: str) -> str | None:
    """Return the Slack user ID for a given email, or None if not found."""
    try:
        response = get_slack_client().users_lookupByEmail(email=email)
        return response["user"]["id"]
    except Exception as exc:
        print(f"[slack] Could not find Slack user for {email}: {exc}")
        return None


def notify_progress(channel: str, text: str, thread_ts: str | None = None) -> None:
    """Post a progress update to Slack. Silently ignores errors so pipeline never blocks."""
    try:
        post_message(channel=channel, text=text, thread_ts=thread_ts)
    except Exception as exc:
        print(f"[slack] Progress notification failed: {exc}")


def post_blocks(channel: str, blocks: list, text: str = "", thread_ts: str | None = None) -> str:
    client = get_slack_client()
    response = client.chat_postMessage(
        channel=channel,
        blocks=blocks,
        text=text,
        thread_ts=thread_ts,
    )
    return response["ts"]
