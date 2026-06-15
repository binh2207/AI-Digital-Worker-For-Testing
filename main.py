"""
Slack trigger: listens for @Quality-Engineer-Bot mentions and kicks off the LangGraph workflow.
"""
import re
import threading
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from config import SLACK_APP_TOKEN, SLACK_BOT_TOKEN
from tools.slack_client import post_message
from graph import workflow
from state import WorkflowState

app = App(token=SLACK_BOT_TOKEN)

BOT_MENTION_PATTERN = re.compile(r"check\s+(?:the\s+)?jira", re.IGNORECASE)


def _run_workflow(channel: str, thread_ts: str, user: str) -> None:
    initial_state: WorkflowState = {
        "slack_channel": channel,
        "slack_thread_ts": thread_ts,
        "triggered_by": user,
        "jira_tickets": [],
        "test_cases": {},
        "test_results": {},
        "automation_scripts": {},
        "test_summary": {},
        "report": "",
        "error": None,
    }

    post_message(
        channel=channel,
        text=":hourglass_flowing_sand: Starting QA pipeline — checking JIRA Review column...",
        thread_ts=thread_ts,
    )

    try:
        final_state = workflow.invoke(initial_state)
        if final_state.get("error"):
            post_message(
                channel=channel,
                text=f":warning: Pipeline error: {final_state['error']}",
                thread_ts=thread_ts,
            )
        elif not final_state.get("jira_tickets"):
            post_message(
                channel=channel,
                text=":information_source: No tickets found in the Review column right now.",
                thread_ts=thread_ts,
            )
    except Exception as exc:
        post_message(
            channel=channel,
            text=f":rotating_light: Unexpected error: {exc}",
            thread_ts=thread_ts,
        )


@app.event("app_mention")
def handle_mention(event, say):
    text = event.get("text", "")
    channel = event["channel"]
    thread_ts = event.get("thread_ts") or event["ts"]
    user = event.get("user", "unknown")

    if not BOT_MENTION_PATTERN.search(text):
        say(
            text="Hi! Mention me with *check the JIRA board* to trigger the QA pipeline.",
            thread_ts=thread_ts,
        )
        return

    # Run the heavy workflow in a background thread so Slack's 3-second ack is met
    threading.Thread(target=_run_workflow, args=(channel, thread_ts, user), daemon=True).start()


if __name__ == "__main__":
    handler = SocketModeHandler(app, SLACK_APP_TOKEN)
    print("Quality-Engineer-Bot is running...")
    handler.start()
