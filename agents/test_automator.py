"""
Node 3 — Test Automator Agent
Reads the structured action log (JSON) produced by test_executor and generates
proper Playwright TypeScript automation scripts following POM conventions.
Falls back to raw narrative text if no action log is available.
"""
import json
import subprocess
from pathlib import Path
from state import WorkflowState
from tools.slack_client import notify_progress
from config import PROJECT_DIR, CLAUDE_CMD

FRAMEWORK_DIR = str(Path(PROJECT_DIR) / "playwright-framework")

CODING_RULES = """
## Playwright Automation Coding Rules

### File locations
- Spec files  : tests/e2e/{ticket_id_lower}.spec.ts
- Page Objects: pages/{FeatureName}Page.ts  (PascalCase, no spaces)
- Base class  : pages/BasePage.ts  (already exists — extend it, do not recreate)

### Spec file conventions
- Import { test, expect } from '@playwright/test' directly (no custom fixture needed)
- Import Page Objects with a RELATIVE path: ../../pages/{PageName}Page
- Group with test.describe('{ticket_id} — {summary}', () => { ... })
- Name each test: 'TC-{nn}: {what it verifies}'
- One logical assertion focus per test
- async/await throughout — no .then()
- No selectors in spec files — all locators live in Page Objects

### Page Object conventions
- Class name: {FeatureName}Page
- Extend BasePage (import with relative path: ./BasePage)
- Declare all Locators as readonly class properties set in constructor
- Methods: goto(), click actions, getters — return Promise<void> or typed value
- No expect() calls inside Page Objects

### Locators (critical)
- Prefer semantic: getByRole(), getByLabel(), getByText(), getByPlaceholder()
- Use the EXACT locator expressions recorded in the action log — do not invent new ones
- CSS/XPath only as last resort

### General
- No hardcoded timeouts
- screenshot/video/trace configured globally — do not add per-test
"""


def _render_steps(steps: list[dict]) -> list[str]:
    """Render a list of step dicts into human-readable lines."""
    lines = []
    for step in steps:
        seq = step.get("seq", "?")
        action = step.get("action", "")
        if action == "navigate":
            lines.append(f"  {seq}. navigate        → {step.get('url', '')}")
        elif action == "click":
            lines.append(f"  {seq}. click           → {step.get('locator', '')}")
        elif action == "fill":
            lines.append(f"  {seq}. fill            → {step.get('locator', '')}  value={step.get('value', '')!r}")
        elif action == "select_option":
            lines.append(f"  {seq}. select_option   → {step.get('locator', '')}  value={step.get('value', '')!r}")
        elif action == "expect_visible":
            lines.append(f"  {seq}. expect_visible  → {step.get('locator', '')}")
        elif action == "expect_text":
            lines.append(f"  {seq}. expect_text     → {step.get('locator', '')}  expected={step.get('expected', '')!r}")
        elif action == "expect_url":
            lines.append(f"  {seq}. expect_url      → {step.get('pattern', '')}")
        else:
            lines.append(f"  {seq}. {action} → {json.dumps(step)}")
    return lines


def _split_by_status(action_log: dict) -> tuple[list[dict], list[dict]]:
    """Return (passed_tcs, failed_tcs) from the action log."""
    passed, failed = [], []
    for tc in action_log.get("test_cases", []):
        (passed if tc.get("status") == "PASSED" else failed).append(tc)
    return passed, failed


def _render_passed_context(base_url: str, passed_tcs: list[dict]) -> str:
    """Render only PASSED test cases with their verified steps/locators."""
    lines = [f"Base URL: {base_url}", ""]
    for tc in passed_tcs:
        lines.append(f"### {tc['id']}: {tc['title']}")
        lines.append("Steps (verified live — use these exact locators):")
        lines.extend(_render_steps(tc.get("steps", [])))
        lines.append("")
    return "\n".join(lines)


def _render_skip_list(failed_tcs: list[dict]) -> str:
    """Render FAILED test cases as a skip list (no steps exposed)."""
    if not failed_tcs:
        return "None"
    return "\n".join(
        f"- {tc['id']}: {tc.get('failure_reason') or 'failed during live execution'}"
        for tc in failed_tcs
    )


def build_test_automator_node():
    def test_automator(state: WorkflowState) -> WorkflowState:
        jira_tickets: list[dict] = state.get("jira_tickets", [])
        test_cases: dict = state.get("test_cases", {})
        test_results: dict = state.get("test_results", {})
        action_logs: dict = state.get("action_logs", {})
        channel = state.get("slack_channel")
        thread_ts = state.get("slack_thread_ts")

        if not test_results:
            return {**state, "error": "No test results to automate."}

        automation_scripts: dict = {}

        for ticket in jira_tickets:
            ticket_id = ticket["id"]
            result = test_results.get(ticket_id, {})
            raw_execution = result.get("raw", "")
            test_cases_md = test_cases.get(ticket_id, "")
            action_log = action_logs.get(ticket_id)

            if not raw_execution and not action_log:
                print(f"[test_automator] {ticket_id}: no execution data, skipping.")
                continue

            spec_name = ticket_id.lower().replace("-", "_")
            page_name = "".join(w.capitalize() for w in ticket["summary"].split()) + "Page"
            page_name = "".join(c for c in page_name if c.isalnum())  # strip punctuation

            if channel:
                notify_progress(channel, f":robot_face: Generating automation scripts for `{ticket_id}`: _{ticket['summary']}_", thread_ts)

            # --- Gate: only automate PASSED test cases ---
            if action_log:
                passed_tcs, failed_tcs = _split_by_status(action_log)
                if not passed_tcs:
                    print(f"[test_automator] {ticket_id}: 0 PASSED test cases — skipping automation.")
                    if channel:
                        notify_progress(channel, f":no_entry: `{ticket_id}` — 0 PASSED test cases, automation skipped.", thread_ts)
                    automation_scripts[ticket_id] = []
                    continue

                automate_context = _render_passed_context(
                    action_log.get("base_url", ""), passed_tcs
                )
                skip_list = _render_skip_list(failed_tcs)
                source_label = f"Structured action log — {len(passed_tcs)} PASSED, {len(failed_tcs)} skipped"
                print(f"[test_automator] {ticket_id}: {len(passed_tcs)} PASSED → automating, {len(failed_tcs)} FAILED → skipping.")
            else:
                # Fallback: no structured log, send raw text and let Claude sort it out
                automate_context = raw_execution[:6000]
                skip_list = "(no action log — infer from narrative above)"
                source_label = "Raw narrative output (action log unavailable)"
                print(f"[test_automator] {ticket_id}: no action log, falling back to raw narrative.")

            prompt = f"""You are a senior QA automation engineer.
Generate a Playwright TypeScript automation spec and Page Object
from the verified live execution data below.

{CODING_RULES}

---

## Ticket
ID: {ticket_id}
Summary: {ticket['summary']}

## PASSED Test Cases — automate ONLY these
The steps below were verified live in a real browser. Use the exact locator
expressions listed here for all Page Object properties.

{automate_context}

## FAILED / Skipped Test Cases — add as comments only, do NOT automate
{skip_list}

---

## Output Instructions

Generate exactly TWO files — no text outside the delimiters.

=== FILE: tests/e2e/{spec_name}.spec.ts ===
<typescript code here>

=== FILE: pages/{page_name}.ts ===
<typescript code here>

Spec rules:
- test() blocks: ONLY the PASSED test cases listed above.
- FAILED cases: one-line comment per case — // SKIP TC-nn: <reason>
- Relative imports: ../../pages/{page_name}  (no @pages alias)
- No assertions inside Page Object methods.
- No hardcoded locators in the spec — everything in the Page Object.
"""

            print(f"[test_automator] Generating automation script for {ticket_id} (source: {'action_log' if action_log else 'raw'}) ...")
            result_claude = subprocess.run(
                [CLAUDE_CMD, "--print", "--output-format", "text"],
                input=prompt,
                capture_output=True, text=True, encoding="utf-8",
                timeout=180, cwd=PROJECT_DIR,
            )

            output = result_claude.stdout.strip()
            if not output:
                print(f"[test_automator] {ticket_id}: no output from Claude.")
                continue

            written_files = []
            sections = output.split("=== FILE:")
            for section in sections[1:]:
                lines = section.strip().splitlines()
                file_path_line = lines[0].strip().rstrip("===").strip()
                code = "\n".join(lines[1:]).strip()

                target = Path(FRAMEWORK_DIR) / file_path_line
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(code, encoding="utf-8")
                written_files.append(str(target))
                print(f"[test_automator] Written: {target}")

            automation_scripts[ticket_id] = written_files

        return {**state, "automation_scripts": automation_scripts}

    return test_automator
