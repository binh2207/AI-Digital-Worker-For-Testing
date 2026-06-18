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
    """Extract and parse the JSON action log block from Claude's output.
    Uses the LAST occurrence in case Claude outputs an empty block first.
    Also strips markdown code fences Claude may wrap around the JSON.
    """
    # Find the last ACTION_LOG_START (Claude sometimes emits an empty one first)
    last_start = raw_output.rfind(ACTION_LOG_START)
    if last_start == -1:
        return None
    last_end = raw_output.find(ACTION_LOG_END, last_start)
    if last_end == -1:
        return None

    content = raw_output[last_start + len(ACTION_LOG_START):last_end].strip()

    # Strip opening ```[lang] and closing ``` fences
    if content.startswith("```"):
        content = content[content.find("\n") + 1:].strip()
    if content.endswith("```"):
        content = content[:content.rfind("```")].strip()

    if not content:
        print(f"[test_executor] Action log block found but content is empty.")
        return None

    try:
        return json.loads(content)
    except json.JSONDecodeError as exc:
        print(f"[test_executor] Failed to parse action log JSON: {exc}")
        print(f"[test_executor] Content was: {content[:200]}")
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

## Site-specific Locator Rules
- Shopify cart page: product name elements are <a> links inside <td> — use getByRole('link', {{ name: /product name/ }}), NOT getByRole('heading'). Record role as "link" in element_attributes.
- Shopify variant naming: Shopify renders "Product - Variant" when both names are identical (e.g. "Grey jacket - Grey jacket"). Always use a regex locator /Grey jacket/ instead of the full duplicate string to avoid fragile exact matches.

## Locator Inspection (required for every click, fill, and assertion step)
Before interacting with any element, inspect its DOM to collect rich metadata:
1. Call evaluate() or use snapshot to read: tag, id, name, data-testid, data-qa, aria-label, role, type, class attributes.
2. Count how many elements the locator matches BEFORE scoping (element_count).
3. Record HOW you resolved ambiguity if element_count > 1: "first" | "filter" | "nth" | "unique" (only 1 match).
4. Record the scope_locator if you scoped to a container first (e.g. ".cart-item" before calling getByRole inside it).
5. Record up to 2 fallback locators in locator_alternatives[] — priority: data-testid/id > CSS with unique attr > role-based.

## MANDATORY: After finishing ALL test cases, append this block at the very end of your response.
Replace ALL placeholders with real data from what you actually observed and did.
Use the exact Playwright locator expressions you called (e.g. getByRole('button', {{ name: /add to cart/i }})).

### Step field reference:
- navigate      : seq, action, url, trigger ("explicit" | "post_click" | "post_form_submit")
- click         : seq, action, locator, locator_alternatives[], element_attributes{{}}, element_count, selector_method, scope_locator, causes_navigation (true|false), wait_for ("none"|"load"|"networkidle"), post_url (if causes_navigation=true)
- fill          : seq, action, locator, locator_alternatives[], element_attributes{{}}, value
- select_option : seq, action, locator, locator_alternatives[], element_attributes{{}}, value
- expect_visible: seq, action, locator, scope_locator, visible_text
- expect_text   : seq, action, locator, scope_locator, expected, visible_text, match_type ("exact"|"contains"|"regex"), dynamic_content (true|false)
- expect_url    : seq, action, pattern

### Field definitions:
- element_attributes: object with actual DOM attributes — {{ "id": "...", "data-testid": "...", "aria-label": "...", "type": "...", "role": "..." }} — only include non-empty ones
- element_count: how many elements matched the locator before any scoping/filtering
- selector_method: "unique" if only 1 match, "first" if used .first(), "filter" if used .filter({{hasText}}), "nth" if used .nth(n)
- scope_locator: the parent container locator string if element was scoped (e.g. ".cart-item", "form#cart"), null if no scope
- causes_navigation: true if clicking loads a new page or URL changes
- wait_for: "load" after full page reload/form submit, "none" for AJAX (e.g. Add to Cart — avoid networkidle to prevent bot-detection), "networkidle" only when page explicitly settles
- post_url: the URL immediately after a causes_navigation=true click (fill in the actual URL landed on)
- visible_text: the exact text content Claude observed on the element at assertion time
- dynamic_content: true if expected text contains order IDs, prices that may change, timestamps, counts — automator will use regex
- match_type: "exact" if full text must match, "contains" if partial is sufficient, "regex" for patterns
- final_url: URL of the page after the last step of this TC

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
      "final_url": "<url of page after last step>",
      "steps": [
        {{
          "seq": 1,
          "action": "navigate",
          "url": "<full url>",
          "trigger": "explicit"
        }},
        {{
          "seq": 2,
          "action": "click",
          "locator": "<exact playwright locator expression>",
          "locator_alternatives": ["<css fallback>", "<role fallback>"],
          "element_attributes": {{ "type": "submit", "id": "add-to-cart" }},
          "element_count": 1,
          "selector_method": "unique",
          "scope_locator": null,
          "causes_navigation": false,
          "wait_for": "none",
          "post_url": null
        }},
        {{
          "seq": 3,
          "action": "fill",
          "locator": "<locator>",
          "locator_alternatives": ["<id/name css fallback>", "<aria-label fallback>"],
          "element_attributes": {{ "id": "<id>", "name": "<name>", "type": "text" }},
          "value": "<text typed>"
        }},
        {{
          "seq": 4,
          "action": "select_option",
          "locator": "<locator>",
          "locator_alternatives": ["<id/name css fallback>"],
          "element_attributes": {{ "id": "<id>", "name": "<name>" }},
          "value": "<option value or label>"
        }},
        {{
          "seq": 5,
          "action": "expect_visible",
          "locator": "<locator>",
          "scope_locator": null,
          "visible_text": "<text observed on element>"
        }},
        {{
          "seq": 6,
          "action": "expect_text",
          "locator": "<locator>",
          "scope_locator": "<parent container locator or null>",
          "expected": "<text>",
          "visible_text": "<full text Claude actually saw>",
          "match_type": "exact",
          "dynamic_content": false
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
            stderr_out = result.stderr.strip()
            if not full_output:
                full_output = stderr_out or "No output from Claude Code executor."

            print(f"[test_executor] {ticket_id}: exit={result.returncode} | stdout={len(result.stdout)} chars | stderr={len(stderr_out)} chars")
            print(f"[test_executor] {ticket_id}: output tail:\n{full_output[-600:]}")
            if stderr_out:
                print(f"[test_executor] {ticket_id}: stderr: {stderr_out[:300]}")

            action_log = _parse_action_log(full_output)
            narrative = _strip_action_log(full_output)

            if action_log:
                tc_count = len(action_log.get('test_cases', []))
                passed = sum(1 for t in action_log.get('test_cases', []) if t.get('status') == 'PASSED')
                print(f"[test_executor] {ticket_id}: action log parsed — {tc_count} test case(s), {passed} PASSED.")
                action_logs[ticket_id] = action_log
            else:
                print(f"[test_executor] {ticket_id}: WARNING — no action log found in output.")

            test_results[ticket_id] = {
                "raw": narrative,
                "action_log": action_log,
                "_exit_code": result.returncode,
            }

        return {**state, "test_results": test_results, "action_logs": action_logs}

    return test_executor
