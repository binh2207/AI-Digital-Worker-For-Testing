"""
Node 2 — Test Executor Agent
Calls Claude Code CLI with Playwright MCP to execute Markdown test cases
live in a real browser. Outputs both a narrative report and a structured
JSON action log (hand-off contract for test_automator).
"""
import json
import re
import subprocess
from pathlib import Path
from state import WorkflowState
from tools.jira_client import get_test_cases_from_comment
from tools.slack_client import notify_progress
from config import PLAYWRIGHT_BASE_URL, PROJECT_DIR, CLAUDE_CMD

MCP_CONFIG_PATH = str(Path(PROJECT_DIR) / "mcp_config.json")

ACTION_LOG_START = "=== ACTION_LOG_START ==="
ACTION_LOG_END = "=== ACTION_LOG_END ==="


def _parse_action_log(raw_output: str) -> dict | None:
    """Extract and parse the JSON action log block from Claude's output."""
    match = re.search(
        re.escape(ACTION_LOG_START) + r"\s*(.*?)\s*" + re.escape(ACTION_LOG_END),
        raw_output,
        re.DOTALL,
    )
    if not match:
        return None
    try:
        return json.loads(match.group(1))
    except json.JSONDecodeError as exc:
        print(f"[test_executor] Failed to parse action log JSON: {exc}")
        return None


def _strip_action_log(raw_output: str) -> str:
    """Remove the JSON block from the narrative text."""
    return re.sub(
        re.escape(ACTION_LOG_START) + r".*?" + re.escape(ACTION_LOG_END),
        "",
        raw_output,
        flags=re.DOTALL,
    ).strip()


def build_test_executor_node():
    def test_executor(state: WorkflowState) -> WorkflowState:
        jira_tickets: list[dict] = state.get("jira_tickets", [])
        channel = state.get("slack_channel")
        thread_ts = state.get("slack_thread_ts")
        if not jira_tickets:
            return {**state, "error": "No tickets to execute tests for."}

        test_results: dict = {}
        action_logs: dict = {}

        for ticket in jira_tickets:
            ticket_id = ticket["id"]

            if channel:
                notify_progress(channel, f":globe_with_meridians: Running live browser tests for `{ticket_id}`: _{ticket['summary']}_", thread_ts)

            test_cases_md = get_test_cases_from_comment(ticket_id)
            if not test_cases_md:
                print(f"[test_executor] {ticket_id}: no test cases in JIRA comment, skipping.")
                test_results[ticket_id] = {"raw": "No test cases found.", "action_log": None, "_exit_code": -1}
                continue

            prompt = f"""You are a QA engineer executing manual test cases live in a real browser.

Execute the following test cases for JIRA ticket {ticket_id}.
Base URL: {PLAYWRIGHT_BASE_URL}

{test_cases_md}

## Execution Instructions
- Use the Playwright browser tools to perform each step exactly as written.
- After each test case, verify the expected result by observing the page.
- Report PASSED or FAILED for each test case with a one-line reason.
- Execute every test case — do not skip any.
- Do NOT generate code. Interact with the browser directly using the available tools.

## MANDATORY: After finishing ALL test cases, append this block at the very end of your response.
Replace the placeholders with real data from what you actually did.
Use the exact Playwright locator expressions you called (e.g. getByRole('button', {{ name: /add to cart/i }})).

{ACTION_LOG_START}
{{
  "ticket_id": "{ticket_id}",
  "base_url": "{PLAYWRIGHT_BASE_URL}",
  "test_cases": [
    {{
      "id": "TC-01",
      "title": "<test case title>",
      "status": "PASSED or FAILED",
      "failure_reason": "<one line or null>",
      "steps": [
        {{
          "seq": 1,
          "action": "navigate",
          "url": "<full url>"
        }},
        {{
          "seq": 2,
          "action": "click",
          "locator": "<exact playwright locator expression>"
        }},
        {{
          "seq": 3,
          "action": "fill",
          "locator": "<locator>",
          "value": "<text typed>"
        }},
        {{
          "seq": 4,
          "action": "select_option",
          "locator": "<locator>",
          "value": "<option value or label>"
        }},
        {{
          "seq": 5,
          "action": "expect_visible",
          "locator": "<locator>"
        }},
        {{
          "seq": 6,
          "action": "expect_text",
          "locator": "<locator>",
          "expected": "<text>"
        }},
        {{
          "seq": 7,
          "action": "expect_url",
          "pattern": "<url substring or regex string>"
        }}
      ]
    }}
  ]
}}
{ACTION_LOG_END}

Only include step types that actually occurred. Use the same action names as shown above.
The JSON must be valid — double-check brackets and quotes before outputting."""

            print(f"\n[test_executor] Executing {ticket_id} live via Claude Code + Playwright MCP ...")
            result = subprocess.run(
                [
                    CLAUDE_CMD, "--print",
                    "--mcp-config", MCP_CONFIG_PATH,
                    "--allowedTools", "mcp__playwright__*",
                    "--output-format", "text",
                ],
                input=prompt, capture_output=True, text=True, encoding="utf-8", timeout=600, cwd=PROJECT_DIR,
            )

            full_output = result.stdout.strip()
            if not full_output:
                full_output = result.stderr.strip() or "No output from Claude Code executor."

            action_log = _parse_action_log(full_output)
            narrative = _strip_action_log(full_output)

            if action_log:
                print(f"[test_executor] {ticket_id}: action log parsed — {len(action_log.get('test_cases', []))} test case(s) recorded.")
                action_logs[ticket_id] = action_log
            else:
                print(f"[test_executor] {ticket_id}: WARNING — no action log found in output.")

            test_results[ticket_id] = {
                "raw": narrative,
                "action_log": action_log,
                "_exit_code": result.returncode,
            }
            print(f"[test_executor] {ticket_id}: exit={result.returncode}")

        return {**state, "test_results": test_results, "action_logs": action_logs}

    return test_executor
