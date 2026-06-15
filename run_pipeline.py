"""
One-shot pipeline runner for CI environments.
Invokes the full LangGraph workflow directly — no Slack Socket Mode loop.

Usage:
    python run_pipeline.py

Env vars (all read from .env or CircleCI context):
    SLACK_CI_CHANNEL  — optional Slack channel to post results to (e.g. #qa-bot-ci)
                        Leave unset to suppress Slack output in CI.
"""
import sys
from state import WorkflowState
from graph import workflow


def main() -> None:
    import os

    ci_channel = os.environ.get("SLACK_CI_CHANNEL", "")

    initial_state: WorkflowState = {
        "slack_channel": ci_channel,
        "slack_thread_ts": None,
        "triggered_by": "circleci",
        "jira_tickets": [],
        "test_cases": {},
        "test_results": {},
        "action_logs": {},
        "automation_scripts": {},
        "github_prs": {},
        "test_summary": {},
        "report": "",
        "error": None,
    }

    print("[run_pipeline] Starting QA pipeline (CI mode) ...")
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
