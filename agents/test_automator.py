"""
Node 3 — Test Automator Agent
Reads the structured action log produced by test_executor, generates Playwright
TypeScript scripts via Claude Code, then pushes them to a new GitHub branch and
opens a PR for review.
"""
import json
import re
import subprocess
from datetime import datetime
from state import WorkflowState
from pathlib import Path
from tools.slack_client import notify_progress
from config import PROJECT_DIR, CLAUDE_CMD

PLAYWRIGHT_DIR = str(Path(PROJECT_DIR) / "playwright-framework")

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
- Prefer semantic locators in this priority order: getByRole() → getByLabel() → getByPlaceholder() → getByTestId() → getByText() → CSS. Never use CSS for interactive elements (buttons, links, inputs).
- Use the EXACT locator expressions recorded in the action log — do not invent new ones
- If the action log provides locator_alternatives, declare them as fallback comments in the Page Object
- CSS/XPath only as last resort for non-interactive elements with no semantic alternative

- NEVER use bare tag selectors like locator('h3'), locator('p'), locator('span') — they match the first element on the page, not the intended one. Always scope with role, text, or attribute: getByRole('heading', { name: '...' }), locator('td a:has-text("...")'), or locator('[data-product-title]')
- NEVER use locator('form') as a scope parent — forms can appear multiple times on a page. Scope to a specific ID or data attribute instead: locator('#cart-form') or locator('[data-section="cart"]')
- Shopify cart page: product names are rendered as <a> links inside <td> cells — use getByRole('link', { name: /product name/ }) NOT getByRole('heading'). Headings do not exist for cart line items.
- Shopify variant naming: when product title and variant title are the same, Shopify renders "Grey jacket - Grey jacket". Use a regex locator to avoid hardcoding the duplicate: getByRole('link', { name: /Grey jacket/ }) instead of { name: 'Grey jacket - Grey jacket' }
- NEVER use .first() or .nth(index) without first scoping to a container. .first() signals an ambiguous locator. Instead: page.locator('.cart-item').filter({ hasText: 'product name' }).getByRole('link')
- When a page has repeated elements (list items, cart rows, table rows), always use .filter({ hasText: '...' }) or .filter({ has: page.locator(...) }) to narrow to the specific item — never rely on DOM order via .nth()

- When using getByText() to locate a price, label, or any element whose full text must match exactly, ALWAYS add { exact: true } — e.g. getByText('£55.00', { exact: true }). Without it, getByText() does substring matching and will pick up surrounding elements like "1 x £55.00"

### Assertions (critical)
- Use toBeVisible() when the user must be able to see the element (checks CSS visibility). Use toBeAttached() only when checking DOM presence regardless of visibility — do not confuse the two.
- Never hardcode dynamic values (timestamps, order IDs, random tokens) in assertions. Use regex instead: toContainText(/Order #\d+/) or toHaveText(/\d{2}\/\d{2}\/\d{4}/)
- If match_type="exact", use toHaveText(expected) — full string match
- If match_type="contains", use toContainText(expected) — partial match
- If match_type="regex", use toHaveText(new RegExp(expected))

### Using action log metadata (critical)
- element_attributes: use to pick the best locator — prefer data-testid/id over role over CSS. If "id" is present, use page.locator('#id'). If "data-testid" is present, use getByTestId('value').
- element_count + selector_method: if count > 1 and method="filter", use .filter({ hasText: '...' }) in the Page Object. If method="nth", use .nth(n). NEVER use .first() when filter is possible.
- scope_locator: if scope_locator is set, chain it: page.locator(scope_locator).getByRole(...) — do not call page.getByRole() directly.
- post_url: if a click step has post_url, add await page.waitForURL(post_url) inside the click method after the click.
- dynamic_content=true: use regex assertion — toContainText(/pattern/) or toHaveText(new RegExp('...')). Do NOT hardcode the exact string.
- visible_text: use as the source of truth for the expected value in assertions — prefer this over the expected field if they differ.

### Navigation & waiting
- If a step has causes_navigation=true, use: await Promise.all([page.waitForURL('**'), locator.click()])
- If a step has wait_for="networkidle", add await page.waitForLoadState('networkidle') after the action
- If a step has wait_for="load", add await page.waitForLoadState('load') after the action
- If a TC has final_url set, add await expect(page).toHaveURL(<final_url pattern>) as the last assertion

### Assertions
- If match_type="exact", use toHaveText(expected) — full string match
- If match_type="contains", use toContainText(expected) — partial match
- If match_type="regex", use toHaveText(new RegExp(expected))

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
            trigger = step.get("trigger", "explicit")
            lines.append(f"  {seq}. navigate        -> {step.get('url', '')}  [trigger={trigger}]")
        elif action == "click":
            locator = step.get("locator", "")
            alts = step.get("locator_alternatives", [])
            nav = step.get("causes_navigation", False)
            wait = step.get("wait_for", "none")
            count = step.get("element_count", "?")
            method = step.get("selector_method", "")
            scope = step.get("scope_locator")
            post_url = step.get("post_url")
            attrs = step.get("element_attributes", {})
            line = f"  {seq}. click           -> {locator}  [causes_navigation={nav}, wait_for={wait}, count={count}, method={method}]"
            if scope:
                line += f"\n       scope: {scope}"
            if post_url:
                line += f"\n       post_url: {post_url}"
            if attrs:
                line += f"\n       attrs: {attrs}"
            if alts:
                line += f"\n       fallbacks: {alts}"
            lines.append(line)
        elif action == "fill":
            locator = step.get("locator", "")
            alts = step.get("locator_alternatives", [])
            attrs = step.get("element_attributes", {})
            line = f"  {seq}. fill            -> {locator}  value={step.get('value', '')!r}"
            if attrs:
                line += f"\n       attrs: {attrs}"
            if alts:
                line += f"\n       fallbacks: {alts}"
            lines.append(line)
        elif action == "select_option":
            locator = step.get("locator", "")
            alts = step.get("locator_alternatives", [])
            attrs = step.get("element_attributes", {})
            line = f"  {seq}. select_option   -> {locator}  value={step.get('value', '')!r}"
            if attrs:
                line += f"\n       attrs: {attrs}"
            if alts:
                line += f"\n       fallbacks: {alts}"
            lines.append(line)
        elif action == "expect_visible":
            scope = step.get("scope_locator")
            visible = step.get("visible_text", "")
            line = f"  {seq}. expect_visible  -> {step.get('locator', '')}"
            if scope:
                line += f"  [scope={scope}]"
            if visible:
                line += f"\n       visible_text: {visible!r}"
            lines.append(line)
        elif action == "expect_text":
            match_type = step.get("match_type", "exact")
            scope = step.get("scope_locator")
            visible = step.get("visible_text", "")
            dynamic = step.get("dynamic_content", False)
            line = f"  {seq}. expect_text     -> {step.get('locator', '')}  expected={step.get('expected', '')!r}  [match={match_type}, dynamic={dynamic}]"
            if scope:
                line += f"\n       scope: {scope}"
            if visible:
                line += f"\n       visible_text: {visible!r}"
            lines.append(line)
        elif action == "expect_url":
            lines.append(f"  {seq}. expect_url      -> {step.get('pattern', '')}")
        else:
            lines.append(f"  {seq}. {action} -> {json.dumps(step)}")
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
        if tc.get("final_url"):
            lines.append(f"Final URL after TC: {tc['final_url']}")
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
        file_path = lines[0].strip().rstrip("===").strip().strip("`")
        content_lines = lines[1:]
        # Strip leading blank lines then opening ```[lang] fence
        while content_lines and content_lines[0].strip() == "":
            content_lines = content_lines[1:]
        if content_lines and content_lines[0].strip().startswith("```"):
            content_lines = content_lines[1:]
        # Strip trailing non-code lines: closing ```, markdown separators (---), blank lines
        while content_lines and content_lines[-1].strip() in ("```", "---", ""):
            content_lines = content_lines[:-1]
        files[file_path] = "\n".join(content_lines)
    return files


# ── Validation (runs after generation, before handing off to healer) ──────────

def _check_tc_coverage(spec_content: str, passed_tcs: list[dict]) -> list[str]:
    """Check 1: every PASSED TC appears as a test() block with matching ID."""
    errors = []
    generated_ids = set(re.findall(r"test\s*\(\s*['\"`](TC-\d+)", spec_content))
    expected_ids = {tc["id"] for tc in passed_tcs}
    missing = expected_ids - generated_ids
    extra = generated_ids - expected_ids
    if missing:
        errors.append(f"TC coverage: missing test() blocks for {sorted(missing)}")
    if extra:
        errors.append(f"TC coverage: unexpected test() blocks {sorted(extra)} not in action log")
    return errors


def _check_locators_in_page_object(page_content: str, passed_tcs: list[dict]) -> list[str]:
    """Check 2: every meaningful locator string from action log appears in page object."""
    errors = []
    for tc in passed_tcs:
        for step in tc.get("steps", []):
            locator = step.get("locator", "")
            if not locator or step.get("action") in ("navigate", "expect_url"):
                continue
            # Extract quoted substrings >= 4 chars (role names, text values, CSS selectors)
            key_parts = re.findall(r"['\"]([^'\"]{4,})['\"]", locator)
            for part in key_parts:
                if part not in page_content:
                    errors.append(
                        f"Locator mismatch: '{part}' (from {tc['id']} step {step.get('seq')}) "
                        f"not found in page object"
                    )
                    break  # one error per step is enough
    return errors


def _check_import_class_match(spec_content: str, page_content: str) -> list[str]:
    """Check 3: exported class name in page object matches import in spec."""
    errors = []
    class_match = re.search(r"export class (\w+)", page_content)
    import_match = re.search(r"import\s*\{([^}]+)\}\s*from", spec_content)
    if not class_match:
        errors.append("Class match: no 'export class' found in page object")
        return errors
    if not import_match:
        errors.append("Class match: no import statement found in spec")
        return errors
    class_name = class_match.group(1).strip()
    imported = [n.strip() for n in import_match.group(1).split(",")]
    if class_name not in imported:
        errors.append(
            f"Class match: page object exports '{class_name}' but spec imports {imported}"
        )
    return errors


def _run_tsc_check() -> tuple[bool, str]:
    """Check 4: TypeScript compile check on the playwright-framework directory."""
    result = subprocess.run(
        "npx tsc --noEmit",
        cwd=PLAYWRIGHT_DIR,
        capture_output=True, text=True, encoding="utf-8", timeout=60,
        shell=True,
    )
    return result.returncode == 0, (result.stdout + result.stderr).strip()


def _validate_generated_files(
    files: dict[str, str],
    passed_tcs: list[dict],
) -> list[str]:
    """Run all 4 checks. Returns list of error strings (empty = all passed)."""
    spec_content = next((c for p, c in files.items() if p.endswith(".spec.ts")), None)
    page_content = next((c for p, c in files.items() if "pages/" in p and p.endswith(".ts")), None)

    if not spec_content:
        return ["No spec file (.spec.ts) found in generated output"]
    if not page_content:
        return ["No page object file (pages/*.ts) found in generated output"]

    errors: list[str] = []
    errors += _check_tc_coverage(spec_content, passed_tcs)
    errors += _check_locators_in_page_object(page_content, passed_tcs)
    errors += _check_import_class_match(spec_content, page_content)
    return errors


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
        automation_file_contents: dict = {}
        github_prs: dict = {}
        timestamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")

        for ticket in jira_tickets:
            ticket_id = ticket["id"]
            result = test_results.get(ticket_id, {})
            raw_execution = result.get("raw", "")
            action_log = action_logs.get(ticket_id)

            # Require a structured action log with at least one PASSED test case
            if not action_log:
                print(f"[test_automator] {ticket_id}: no action log — skipping automation.")
                if channel:
                    notify_progress(channel, f":no_entry: `{ticket_id}` — no structured action log, automation skipped.", thread_ts)
                continue

            passed_tcs, failed_tcs = _split_by_status(action_log)
            if not passed_tcs:
                print(f"[test_automator] {ticket_id}: 0 PASSED test cases — skipping automation.")
                if channel:
                    notify_progress(channel,
                        f":no_entry: `{ticket_id}` — 0 PASSED test cases ({len(failed_tcs)} failed), automation skipped.",
                        thread_ts)
                continue

            spec_name = ticket_id.lower().replace("-", "_")
            page_name = "".join(w.capitalize() for w in ticket["summary"].split()) + "Page"
            page_name = "".join(c for c in page_name if c.isalnum())

            automate_context = _render_passed_context(action_log.get("base_url", ""), passed_tcs)
            skip_list = _render_skip_list(failed_tcs)
            source_label = f"Structured action log — {len(passed_tcs)} PASSED, {len(failed_tcs)} skipped"
            print(f"[test_automator] {ticket_id}: {len(passed_tcs)} PASSED -> automating, {len(failed_tcs)} FAILED -> skipping.")

            if channel:
                notify_progress(channel,
                    f":robot_face: Generating scripts for `{ticket_id}` — {len(passed_tcs)} PASSED test case(s): _{ticket['summary']}_",
                    thread_ts)

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
                timeout=300, cwd=PROJECT_DIR,
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
                print(f"[test_automator] {ticket_id}: raw output (first 800 chars):\n{output[:800]}")
                continue

            # Write files to local playwright-framework directory
            for rel_path, content in files.items():
                local_path = Path(PROJECT_DIR) / rel_path
                local_path.parent.mkdir(parents=True, exist_ok=True)
                local_path.write_text(content, encoding="utf-8")
                print(f"[test_automator] {ticket_id}: saved locally → {rel_path}")

            # ── Validation checks ────────────────────────────────────────────
            # Check 1-3: structural validation (TC coverage, locators, class import)
            val_errors = _validate_generated_files(files, passed_tcs)
            if val_errors:
                print(f"[test_automator] {ticket_id}: ⚠ validation errors ({len(val_errors)}):")
                for err in val_errors:
                    print(f"  - {err}")
                if channel:
                    err_summary = "\n".join(f"• {e}" for e in val_errors)
                    notify_progress(channel,
                        f":warning: `{ticket_id}` — {len(val_errors)} validation issue(s) detected, healer will fix:\n{err_summary}",
                        thread_ts)
            else:
                print(f"[test_automator] {ticket_id}: ✓ structural validation passed (TC coverage, locators, class import).")

            # Check 4: TypeScript compile check
            tsc_ok, tsc_out = _run_tsc_check()
            if not tsc_ok:
                print(f"[test_automator] {ticket_id}: ✗ tsc check FAILED:\n{tsc_out[:500]}")
                if channel:
                    notify_progress(channel,
                        f":x: `{ticket_id}` — TypeScript compile error detected before healing:\n```{tsc_out[:300]}```",
                        thread_ts)
            else:
                print(f"[test_automator] {ticket_id}: ✓ tsc check PASSED.")

            # Store validation result in source_label for PR body context
            val_status = f"✓ clean" if (not val_errors and tsc_ok) else f"⚠ {len(val_errors)} structural + {'tsc fail' if not tsc_ok else 'tsc ok'}"

            # Store scripts in state — GitHub push happens after self-healing
            branch_name = f"qa-bot/{ticket_id.lower()}-{timestamp}"
            automation_scripts[ticket_id] = list(files.keys())
            automation_file_contents[ticket_id] = files
            github_prs[ticket_id] = {
                "branch": branch_name,
                "summary": ticket["summary"],
                "source_label": f"{source_label} | pre-heal validation: {val_status}",
            }
            print(f"[test_automator] {ticket_id}: {len(files)} file(s) saved locally and staged for self-healing.")
            if channel:
                notify_progress(channel, f":hourglass: `{ticket_id}` — scripts generated and saved locally, handing off to self-healer before pushing PR.", thread_ts)

        return {**state, "automation_scripts": automation_scripts, "automation_file_contents": automation_file_contents, "github_prs": github_prs}

    return test_automator
