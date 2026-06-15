"""
One-shot pipeline runner.
Invokes the full LangGraph workflow directly — no Slack Socket Mode loop.

Environment variables (optional — set by the trigger source e.g. Jenkins):
  SLACK_TRIGGER_CHANNEL    — Slack channel to post progress + final report
  SLACK_TRIGGER_THREAD_TS  — Thread timestamp to reply into the right thread
  TRIGGERED_BY             — Who triggered the pipeline (user ID or system name)

Usage:
    python run_pipeline.py
"""
import os
import sys

from graph import workflow
from state import WorkflowState


def main() -> None:
    slack_channel   = os.environ.get("SLACK_TRIGGER_CHANNEL", "")
    slack_thread_ts = os.environ.get("SLACK_TRIGGER_THREAD_TS") or None
    triggered_by    = os.environ.get("TRIGGERED_BY", "pipeline")

    initial_state: WorkflowState = {
        "slack_channel":   slack_channel,
        "slack_thread_ts": slack_thread_ts,
        "triggered_by":    triggered_by,
        "jira_tickets":    [],
        "test_cases":      {},
        "test_results":    {},
        "action_logs":     {},
        "automation_scripts": {},
        "github_prs":      {},
        "test_summary":    {},
        "report":          "",
        "error":           None,
    }

    print(f"[run_pipeline] Starting QA pipeline — triggered by {triggered_by}")
    if slack_channel:
        print(f"[run_pipeline] Slack thread: {slack_channel} / {slack_thread_ts}")

    final_state = workflow.invoke(initial_state)

    if final_state.get("error"):
        print(f"[run_pipeline] Pipeline error: {final_state['error']}")
        sys.exit(1)

    if not final_state.get("jira_tickets"):
        print("[run_pipeline] No tickets found in Review column — nothing to do.")
        sys.exit(0)

    prs = final_state.get("github_prs", {})
    if prs:
        print("\n[run_pipeline] PRs created:")
        for ticket_id, pr in prs.items():
            print(f"  {ticket_id}: {pr['pr_url']}  (branch: {pr['branch']})")

    print("\n[run_pipeline] Report:")
    print(final_state.get("report", "(no report)"))


if __name__ == "__main__":
    main()
