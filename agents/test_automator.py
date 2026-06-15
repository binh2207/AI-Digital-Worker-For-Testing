"""
Node 3 — Test Automator Agent
Reads the structured action log produced by test_executor, generates Playwright
TypeScript scripts via Claude Code, then pushes them to a new GitHub branch and
opens a PR for review.
"""
import json
import subprocess
from datetime import datetime
from state import WorkflowState
from tools.slack_client import notify_progress
from tools.github_client import create_branch, commit_files, create_pull_request
from config import PROJECT_DIR, CLAUDE_CMD, GITHUB_DEFAULT_BRANCH

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
    passed, failed = [], []
    for tc in action_log.get("test_cases", []):
        (passed if tc.get("status") == "PASSED" else failed).append(tc)
    return passed, failed


def _render_passed_context(base_url: str, passed_tcs: list[dict]) -> str:
    lines = [f"Base URL: {base_url}", ""]
    for tc in passed_tcs:
        lines.append(f"### {tc['id']}: {tc['title']}")
        lines.append("Steps (verified live — use these exact locators):")
        lines.extend(_render_steps(tc.get("steps", [])))
        lines.append("")
    return "\n".join(lines)


def _render_skip_list(failed_tcs: list[dict]) -> str:
    if not failed_tcs:
        return "None"
    return "\n".join(
        f"- {tc['id']}: {tc.get('failure_reason') or 'failed during live execution'}"
        for tc in failed_tcs
    )


def _parse_files(claude_output: str) -> dict[str, str]:
    """
    Parse Claude's output into {relative_path: content}.
    Handles '=== FILE: path ===' delimiters.
    """
    files: dict[str, str] = {}
    sections = claude_output.split("=== FILE:")
    for section in sections[1:]:
        lines = section.strip().splitlines()
        file_path = lines[0].strip().rstrip("===").strip()
        content = "\n".join(lines[1:]).strip()
        files[file_path] = content
    return files


def build_test_automator_node():
    def test_automator(state: WorkflowState) -> WorkflowState:
        jira_tickets: list[dict] = state.get("jira_tickets", [])
        test_results: dict = state.get("test_results", {})
        action_logs: dict = state.get("action_logs", {})
        channel = state.get("slack_channel")
        thread_ts = state.get("slack_thread_ts")

        if not test_results:
            return {**state, "error": "No test results to automate."}

        automation_scripts: dict = {}
        github_prs: dict = {}
        timestamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")

        for ticket in jira_tickets:
            ticket_id = ticket["id"]
            result = test_results.get(ticket_id, {})
            raw_execution = result.get("raw", "")
            action_log = action_logs.get(ticket_id)

            if not raw_execution and not action_log:
                print(f"[test_automator] {ticket_id}: no execution data, skipping.")
                continue

            spec_name = ticket_id.lower().replace("-", "_")
            page_name = "".join(w.capitalize() for w in ticket["summary"].split()) + "Page"
            page_name = "".join(c for c in page_name if c.isalnum())

            if channel:
                notify_progress(channel, f":robot_face: Generating automation scripts for `{ticket_id}`: _{ticket['summary']}_", thread_ts)

            # Gate: only automate PASSED test cases
            if action_log:
                passed_tcs, failed_tcs = _split_by_status(action_log)
                if not passed_tcs:
                    print(f"[test_automator] {ticket_id}: 0 PASSED test cases — skipping automation.")
                    if channel:
                        notify_progress(channel, f":no_entry: `{ticket_id}` — 0 PASSED test cases, automation skipped.", thread_ts)
                    automation_scripts[ticket_id] = []
                    continue

                automate_context = _render_passed_context(action_log.get("base_url", ""), passed_tcs)
                skip_list = _render_skip_list(failed_tcs)
                source_label = f"Structured action log — {len(passed_tcs)} PASSED, {len(failed_tcs)} skipped"
                print(f"[test_automator] {ticket_id}: {len(passed_tcs)} PASSED → automating, {len(failed_tcs)} FAILED → skipping.")
            else:
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

=== FILE: playwright-framework/tests/e2e/{spec_name}.spec.ts ===
<typescript code here>

=== FILE: playwright-framework/pages/{page_name}.ts ===
<typescript code here>

Spec rules:
- test() blocks: ONLY the PASSED test cases listed above.
- FAILED cases: one-line comment per case — // SKIP TC-nn: <reason>
- Relative imports: ../../pages/{page_name}  (no @pages alias)
- No assertions inside Page Object methods.
- No hardcoded locators in the spec — everything in the Page Object.
"""

            print(f"[test_automator] Calling Claude to generate scripts for {ticket_id} ...")
            result_claude = subprocess.run(
                [CLAUDE_CMD, "--print", "--output-format", "text"],
                input=prompt,
                capture_output=True, text=True, encoding="utf-8",
                timeout=180, cwd=PROJECT_DIR,
            )

            output = result_claude.stdout.strip()
            if not output:
                stderr_hint = result_claude.stderr.strip()[:300] if result_claude.stderr else ""
                print(f"[test_automator] {ticket_id}: no output from Claude (exit={result_claude.returncode}). stderr: {stderr_hint}")
                if channel:
                    notify_progress(channel, f":warning: `{ticket_id}` — Claude returned no output (exit {result_claude.returncode}). Check ANTHROPIC_API_KEY.", thread_ts)
                continue

            files = _parse_files(output)
            if not files:
                print(f"[test_automator] {ticket_id}: could not parse any files from Claude output.")
                continue

            # Push to GitHub
            branch_name = f"qa-bot/{ticket_id.lower()}-{timestamp}"
            pr_title = f"[QA Bot] {ticket_id} — {ticket['summary']}"
            pr_body = (
                f"## Auto-generated by Quality-Engineer-Bot\n\n"
                f"**Ticket:** {ticket_id} — {ticket['summary']}\n"
                f"**Source:** {source_label}\n\n"
                f"### Files\n"
                + "\n".join(f"- `{p}`" for p in files)
                + "\n\n"
                f"Run `npx playwright test` on this branch to verify script quality.\n\n"
                f"> Do **not** merge manually — this PR is managed by QA Bot."
            )

            try:
                print(f"[test_automator] Creating branch {branch_name} ...")
                create_branch(branch_name, from_branch=GITHUB_DEFAULT_BRANCH)

                print(f"[test_automator] Committing {len(files)} file(s) to {branch_name} ...")
                commit_files(
                    branch_name=branch_name,
                    files=files,
                    message=f"feat(qa-bot): add automation scripts for {ticket_id}",
                )

                print(f"[test_automator] Opening PR for {ticket_id} ...")
                pr = create_pull_request(
                    branch_name=branch_name,
                    base_branch=GITHUB_DEFAULT_BRANCH,
                    title=pr_title,
                    body=pr_body,
                )

                github_prs[ticket_id] = {
                    "branch": branch_name,
                    "pr_url": pr["url"],
                    "pr_number": pr["number"],
                }

                print(f"[test_automator] PR #{pr['number']} opened: {pr['url']}")
                if channel:
                    notify_progress(
                        channel,
                        f":github: PR #{pr['number']} created for `{ticket_id}`: {pr['url']}\nBranch: `{branch_name}`",
                        thread_ts,
                    )

            except Exception as exc:
                print(f"[test_automator] GitHub push failed for {ticket_id}: {exc}")
                if channel:
                    notify_progress(channel, f":warning: GitHub push failed for `{ticket_id}`: {exc}", thread_ts)
                continue  # do not record scripts that were never pushed

            automation_scripts[ticket_id] = list(files.keys())

        return {**state, "automation_scripts": automation_scripts, "github_prs": github_prs}

    return test_automator
