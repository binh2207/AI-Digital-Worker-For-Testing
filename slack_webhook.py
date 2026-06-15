"""
Slack webhook — receives @bot mentions and triggers the CircleCI QA pipeline.

Deploy this anywhere with a public URL (Railway, Render, Fly.io, etc.)
then configure Slack Event Subscriptions to point at:
  https://your-host/slack/events

This replaces main.py's Socket Mode loop. It does ONE thing: receive a
Slack event and fire a CircleCI pipeline trigger. CircleCI does all the work.
"""
import hashlib
import hmac
import os
import re
import time

import requests
from flask import Flask, Response, abort, jsonify, request

BOT_MENTION_PATTERN = re.compile(r"check\s+(?:the\s+)?jira", re.IGNORECASE)

app = Flask(__name__)


# ── Helpers ────────────────────────────────────────────────────────────────────

def _verify_slack_signature() -> bool:
    """Reject requests not signed by Slack."""
    signing_secret = os.environ.get("SLACK_SIGNING_SECRET", "").encode()
    timestamp = request.headers.get("X-Slack-Request-Timestamp", "0")
    slack_sig = request.headers.get("X-Slack-Signature", "")

    if abs(time.time() - int(timestamp)) > 300:
        return False  # replay-attack guard

    sig_base = f"v0:{timestamp}:{request.get_data(as_text=True)}"
    expected = "v0=" + hmac.new(signing_secret, sig_base.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, slack_sig)


def _post_slack(channel: str, text: str, thread_ts: str | None = None) -> None:
    requests.post(
        "https://slack.com/api/chat.postMessage",
        headers={"Authorization": f"Bearer {os.environ['SLACK_BOT_TOKEN']}"},
        json={"channel": channel, "text": text, "thread_ts": thread_ts, "mrkdwn": True},
        timeout=10,
    )


def _trigger_circleci(channel: str, thread_ts: str, user: str) -> bool:
    """Fire the qa_pipeline_ci workflow on CircleCI. Returns True on success."""
    repo = os.environ["GITHUB_REPO"]          # binh2207/AI-Digital-Worker-For-Testing
    branch = os.environ.get("GITHUB_DEFAULT_BRANCH", "master")
    token = os.environ["CIRCLECI_TOKEN"]

    resp = requests.post(
        f"https://circleci.com/api/v2/project/github/{repo}/pipeline",
        headers={"Circle-Token": token, "Content-Type": "application/json"},
        json={
            "branch": branch,
            "parameters": {
                "slack_channel":   channel,
                "slack_thread_ts": thread_ts,
                "triggered_by":    user,
            },
        },
        timeout=15,
    )
    if not resp.ok:
        print(f"[webhook] CircleCI trigger failed: {resp.status_code} {resp.text[:300]}")
    return resp.ok


# ── Route ─────────────────────────────────────────────────────────────────────

@app.route("/slack/events", methods=["POST"])
def slack_events():
    if not _verify_slack_signature():
        abort(403)

    payload = request.json or {}

    # One-time URL verification during Slack app setup
    if payload.get("type") == "url_verification":
        return jsonify({"challenge": payload["challenge"]})

    event = payload.get("event", {})
    if event.get("type") != "app_mention":
        return jsonify({"ok": True})

    text      = event.get("text", "")
    channel   = event["channel"]
    thread_ts = event.get("thread_ts") or event["ts"]
    user      = event.get("user", "unknown")

    if not BOT_MENTION_PATTERN.search(text):
        _post_slack(
            channel,
            "Hi! Mention me with *check the JIRA board* to trigger the QA pipeline.",
            thread_ts,
        )
        return jsonify({"ok": True})

    _post_slack(channel, ":hourglass_flowing_sand: Triggering QA pipeline on CircleCI...", thread_ts)

    if not _trigger_circleci(channel, thread_ts, user):
        _post_slack(channel, ":rotating_light: Failed to trigger CircleCI pipeline. Check webhook logs.", thread_ts)

    # Slack requires a response within 3 s — always return 200 immediately
    return jsonify({"ok": True})


@app.route("/health", methods=["GET"])
def health():
    return Response("ok", status=200)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 3000))
    app.run(host="0.0.0.0", port=port)
