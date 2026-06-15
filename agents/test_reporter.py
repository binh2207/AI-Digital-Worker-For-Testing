"""
Node 3 — Test Reporter Agent
Calls Claude Code CLI to summarise live test execution results,
updates JIRA tickets, and posts a report to Slack.
"""
import re
import subprocess
from state import WorkflowState
from tools.jira_client import add_comment, transition_ticket
from tools.slack_client import post_message, lookup_user_id
from config import PROJECT_DIR, CLAUDE_CMD


def _derive_status(raw: str, exit_code: int) -> tuple[str, int, int]:
    text = raw.upper()
    passed = len(re.findall(r'\bPASSED\b', text))
    failed = len(re.findall(r'\bFAILED\b', text))
    if exit_code == -1:
        return "ERROR", 0, 0
    if failed == 0 and passed > 0:
        return "PASSED", passed, 0
    if passed == 0 and failed > 0:
        return "FAILED", 0, failed
    if passed > 0 and failed > 0:
        return "PARTIAL", passed, failed
    return ("PASSED" if exit_code == 0 else "FAILED"), passed, failed


def build_test_reporter_node():
    def test_reporter(state: WorkflowState) -> WorkflowState:
        test_results: dict = state.get("test_results", {})
        jira_tickets: list[dict] = state.get("jira_tickets", [])
        slack_channel = state.get("slack_channel", "")
        slack_thread_ts = state.get("slack_thread_ts")

        if not test_results:
            return {**state, "error": "No test results to report."}

        ticket_map = {t["id"]: t for t in jira_tickets}
        test_summary: dict = {}
        report_lines: list[str] = ["*Quality-Engineer-Bot — Test Execution Report*\n"]

        for ticket_id, result in test_results.items():
            raw = result.get("raw", "")
            exit_code = result.get("_exit_code", -1)
            status, passed, failed = _derive_status(raw, exit_code)

            prompt = f"""You are a QA lead summarising live browser test execution results for stakeholders.

Ticket: {ticket_id}
Summary: {ticket_map.get(ticket_id, {}).get('summary', '')}

Execution output:
{raw[:4000]}

Write a concise Slack-ready summary (plain text, under 15 lines):
- Overall status: {status}
- Passed: {passed} | Failed: {failed}
- Bullet list of failed test cases with one-line reason each (if any)
- Brief recommendation: "Ready to merge" or "Needs fixes before merge"

No markdown headers, no code blocks."""

            print(f"[test_reporter] Generating summary for {ticket_id} ...")
            result_claude = subprocess.run(
                [CLAUDE_CMD, "--print", "--output-format", "text"],
                input=prompt, capture_output=True, text=True, encoding="utf-8", timeout=60, cwd=PROJECT_DIR,
            )
            summary_text = result_claude.stdout.strip() or raw[:500]
            test_summary[ticket_id] = summary_text

            jira_comment = (
                f"*[Quality-Engineer-Bot] Live Test Results — {status}*\n\n"
                f"Passed: {passed} | Failed: {failed}\n\n"
                f"{summary_text}"
            )
            try:
                add_comment(ticket_id, jira_comment)
                if status == "PASSED":
                    transition_ticket(ticket_id, "Done")
                elif status in ("FAILED", "PARTIAL"):
                    transition_ticket(ticket_id, "In Progress")
            except Exception as exc:
                print(f"[test_reporter] JIRA update failed for {ticket_id}: {exc}")

            github_prs = state.get("github_prs", {})
            pr_info = github_prs.get(ticket_id)
            pr_note = ""
            if pr_info:
                pr_note = (
                    f"\n:github: <{pr_info['pr_url']}|PR #{pr_info['pr_number']}> created on branch `{pr_info['branch']}`"
                    f" — automation scripts ready for review."
                )

            icon = ":white_check_mark:" if status == "PASSED" else ":x:"
            report_lines.append(
                f"{icon} *{ticket_id}* — {ticket_map.get(ticket_id, {}).get('summary', '')}\n"
                f"Status: *{status}* | Passed: {passed} | Failed: {failed}\n"
                f"{summary_text}{pr_note}\n"
            )

        full_report = "\n".join(report_lines)

        # Post full report back into the original thread (skip in CI mode where channel is empty)
        if slack_channel:
            try:
                post_message(channel=slack_channel, text=full_report, thread_ts=slack_thread_ts)
            except Exception as exc:
                print(f"[test_reporter] Slack thread post failed: {exc}")

        # Build per-ticket mention lines for dev-channel
        mention_lines: list[str] = []
        for ticket in jira_tickets:
            ticket_id = ticket["id"]
            if ticket_id not in test_summary:
                continue
            result = test_results.get(ticket_id, {})
            raw = result.get("raw", "")
            exit_code = result.get("_exit_code", -1)
            status, passed, failed = _derive_status(raw, exit_code)

            assignee_email = ticket.get("assignee_email")
            slack_uid = lookup_user_id(assignee_email) if assignee_email else None
            mention = f"<@{slack_uid}>" if slack_uid else f"`{ticket.get('assignee', 'Unassigned')}`"

            icon = ":white_check_mark:" if status == "PASSED" else ":x:"
            action = "ready to merge :tada:" if status == "PASSED" else "needs fixes before merge :hammer:"
            mention_lines.append(
                f"{icon} *{ticket_id}* — {ticket['summary']}\n"
                f"Status: *{status}* | {passed} passed / {failed} failed — {action}\n"
                f"Assignee: {mention} please review and take action."
            )

        if mention_lines:
            dev_report = (
                "*Quality-Engineer-Bot — Test Summary* :robot_face:\n\n"
                + "\n\n".join(mention_lines)
            )
            try:
                post_message(channel="#dev-channel", text=dev_report)
                print("[test_reporter] Summary posted to #dev-channel.")
            except Exception as exc:
                print(f"[test_reporter] Failed to post to #dev-channel: {exc}")

        return {**state, "test_summary": test_summary, "report": full_report}

    return test_reporter
