"""
Node 4 — Self-Healing Agent
Runs generated Playwright scripts locally, detects failures,
and calls Claude Code CLI to fix them — up to MAX_ATTEMPTS retries.
Pushes the final (healed or not) files back to the same GitHub branch.
"""
import re
import subprocess
from pathlib import Path
from state import WorkflowState
from tools.slack_client import notify_progress
from tools.github_client import create_branch, commit_files, create_pull_request
from tools.claude_client import call_claude
from config import PROJECT_DIR, GITHUB_DEFAULT_BRANCH

MAX_ATTEMPTS = 4
PLAYWRIGHT_DIR = str(Path(PROJECT_DIR) / "playwright-framework")

COMPILE_ERROR_HINTS = ("SyntaxError", "error TS", "Cannot find", "Module not found", "Object.<anonymous>")

# Fix playbook — ordered strategies per error type, indexed by attempt number (0-based)
FIX_PLAYBOOK: dict[str, list[str]] = {
    "LOCATOR_TIMEOUT": [
        "Replace the failing locator with locator_alternatives[0] declared in the Page Object comments. Use it as-is.",
        "Scope the locator to its container: check scope_locator comments in the Page Object and use page.locator(scope).locator(...). Add .filter({ hasText: '...' }) if element_count > 1.",
        "Add await expect(locator).toBeAttached({ timeout: 10000 }) before the interaction to wait for DOM presence, then interact.",
        "Try locator_alternatives[1] or the CSS fallback from Page Object comments. If none, build a CSS selector from element_attributes (id/data-testid first).",
        "Replace the entire locator with a direct attribute selector: page.locator('[data-testid=\"...\"]') or page.locator('#id') derived from element_attributes in Page Object comments.",
    ],
    "ASSERTION_MISMATCH": [
        "Switch toHaveText to toContainText — the element likely has surrounding whitespace or sibling text nodes.",
        "Replace the expected string with the exact visible_text value recorded in Page Object comments for this locator.",
        "Add { exact: true } to the getByText() locator if missing. If already present, remove it and use toContainText instead.",
        "Convert to regex assertion: toHaveText(new RegExp(pattern)) — escape special characters in the pattern.",
        "Scope the locator to its parent container using scope_locator from Page Object comments to avoid matching sibling elements.",
    ],
    "COMPILE_ERROR": [
        "Fix import paths and verify the exported class name in the Page Object matches exactly what the spec imports.",
        "Fix TypeScript type errors: check property declarations, missing async/await keywords, and wrong return types on Page Object methods.",
        "Add any Page Object properties that the spec references but are not declared. Check the spec for all cartPage.* or equivalent usages.",
        "Fix module resolution: verify the relative import path depth (../../pages/ vs ../pages/) matches the actual file structure.",
        "Remove any syntax errors: unclosed brackets, missing semicolons, invalid TypeScript generics.",
    ],
    "NAVIGATION_TIMEOUT": [
        "Replace Promise.all([page.waitForURL('**'), locator.click()]) with sequential: await locator.click(); await page.waitForLoadState('load').",
        "Remove waitForURL entirely — use waitForLoadState('domcontentloaded') which is faster and less strict.",
        "Add a specific URL pattern to waitForURL using the post_url value from Page Object comments if available.",
        "Wrap navigation in a try/catch and add page.waitForTimeout(1000) before retrying the assertion after click.",
        "Skip waitForNavigation entirely — rely on Playwright's auto-waiting on the next locator interaction.",
    ],
    "AMBIGUOUS_LOCATOR": [
        "Use .filter({ hasText: /pattern/ }) to narrow the ambiguous locator to the specific element — pick the pattern from the test's expected text.",
        "Scope the locator to its parent container: find the nearest unique ancestor (e.g. '.cart__footer', 'table', 'form') and chain page.locator(parent).locator(element).",
        "Replace the CSS selector with a role-based locator: getByRole(..., { name: /pattern/ }) which is inherently unique by name.",
        "Use .nth(0) as a temporary measure only if the first matched element is the correct one — but also add a TODO comment to make it specific.",
        "Build a fully unique CSS selector from element_attributes (id/data-testid first) observed in the Playwright error output suggestion.",
    ],
    "UNKNOWN": [
        "Read the full error message carefully. Fix the most specific error first — focus on the first failing test only.",
        "Check if the error is a selector issue: replace the locator with a simpler CSS selector using tag + unique attribute.",
        "Add explicit waits: before each assertion add await expect(locator).toBeVisible({ timeout: 8000 }).",
        "Simplify the test: remove chained assertions and split them into separate expect() calls to isolate which one fails.",
        "Check for async issues: ensure every Page Object method is async and every call site uses await.",
    ],
}

def _select_strategy(error_type: str, error_output: str, files: dict[str, str], attempt: int) -> str:
    """Dynamically select fix strategy based on actual error content, file state, and attempt number."""
    page_content = " ".join(c for p, c in files.items() if "pages/" in p and p.endswith(".ts"))

    def _fallback(et: str) -> str:
        pool = FIX_PLAYBOOK.get(et, FIX_PLAYBOOK["UNKNOWN"])
        return pool[min(attempt, len(pool) - 1)]

    # ── LOCATOR_TIMEOUT ────────────────────────────────────────────────────────
    if error_type == "LOCATOR_TIMEOUT":
        # Shopify heading/link mismatch
        if re.search(r"getByRole\(['\"]heading['\"]", error_output):
            return (
                "Change getByRole('heading') to getByRole('link', {{ name: /pattern/ }}) — "
                "Shopify cart renders product names as <a> links inside <td>, not heading elements."
            )
        # iframe
        if re.search(r"iframe", error_output, re.IGNORECASE):
            return "Element is inside an iframe. Use page.frameLocator('iframe').locator(...) instead of page.locator(...)."
        # Has fallback locators in page object
        if re.search(r"fallbacks:|locator_alternatives", page_content) and attempt == 0:
            return "Replace the failing locator with the first fallback declared in the Page Object comments (look for '// fallbacks:')."
        # Has scope_locator comment
        if re.search(r"scope:|scope_locator", page_content):
            return (
                "Apply scope from Page Object comments: chain page.locator(scope).locator(element) "
                "instead of calling page.locator(element) directly at page level."
            )
        return _fallback(error_type)

    # ── ASSERTION_MISMATCH ────────────────────────────────────────────────────
    elif error_type == "ASSERTION_MISMATCH":
        expected_m = re.search(r'Expected[^"\n]*"([^"]{1,80})"', error_output)
        received_m = re.search(r'Received[^"\n]*"([^"]{1,80})"', error_output)

        if expected_m and received_m:
            expected = expected_m.group(1).strip()
            received = received_m.group(1).strip()

            if not received or received.isspace():
                return (
                    "Received is empty string — the locator is matching a wrong/invisible element. "
                    "Fix the locator scope before fixing the assertion value."
                )
            if expected in received:
                return (
                    f"Expected '{expected}' is a substring of received '{received}' — "
                    f"the locator matches a parent element containing more text. "
                    f"Either scope to the specific child element or switch to toContainText('{expected}')."
                )
            if received in expected:
                return (
                    f"Received '{received}' is shorter than expected — "
                    f"use toContainText('{received}') or update expected to '{received}'."
                )
            # Completely different text
            return (
                f"Expected '{expected[:50]}' but got completely different text '{received[:50]}' — "
                f"the locator is targeting the wrong element. "
                f"Check scope_locator in Page Object comments and narrow the selector."
            )

        if re.search(r"toBeVisible.*failed", error_output, re.IGNORECASE):
            return (
                "toBeVisible() failed — element is in DOM but hidden. "
                "Try scrollIntoViewIfNeeded() before the assertion, or check if a modal/overlay is blocking."
            )
        return _fallback(error_type)

    # ── COMPILE_ERROR ─────────────────────────────────────────────────────────
    elif error_type == "COMPILE_ERROR":
        if "No tests found" in error_output and not re.search(r"error TS\d+", error_output):
            return (
                "Playwright reported 'No tests found' — the spec file failed to parse. "
                "Check: (1) import path depth matches actual file location (../../pages/ vs ../pages/), "
                "(2) exported class name in Page Object exactly matches the import in spec, "
                "(3) no stray characters outside test() blocks."
            )
        ts_errors = re.findall(r"error TS\d+: (.+)", error_output)
        if ts_errors:
            first = ts_errors[0].strip()
            if re.search(r"Cannot find module|Cannot find name", first):
                return (
                    f"Fix import/module error: '{first}'. "
                    f"Check relative path depth (../../pages/ vs ../pages/) and file name casing (Linux is case-sensitive)."
                )
            if re.search(r"does not exist on type|Property .* not found", first):
                return (
                    f"Missing property: '{first}'. "
                    f"Add the missing Locator property declaration to the Page Object class constructor."
                )
            if re.search(r"is not assignable|Type .* is not", first):
                return f"Type mismatch: '{first}'. Fix the type annotation or return type on the affected method."
            return f"TypeScript error: '{first}'. Fix the root cause of this specific error only."
        return _fallback(error_type)

    # ── NAVIGATION_TIMEOUT ────────────────────────────────────────────────────
    elif error_type == "NAVIGATION_TIMEOUT":
        if re.search(r"waitForURL|waitForNavigation", error_output):
            return (
                "Replace Promise.all([page.waitForURL(...), click()]) with sequential: "
                "await locator.click(); await page.waitForLoadState('load')."
            )
        return _fallback(error_type)

    # ── AMBIGUOUS_LOCATOR ─────────────────────────────────────────────────────
    elif error_type == "AMBIGUOUS_LOCATOR":
        count_m = re.search(r"resolved to (\d+) elements", error_output)
        locator_m = re.search(r"Locator: (.+)", error_output)
        count_info = f" (resolved to {count_m.group(1)} elements)" if count_m else ""
        locator_info = f" Failing locator: `{locator_m.group(1).strip()}`." if locator_m else ""

        # Playwright often suggests a fix in the error output — extract it
        suggestion_m = re.search(r"aka (getBy\w+\([^)]+\)|locator\([^)]+\)\.filter\([^)]+\))", error_output)
        if suggestion_m:
            return (
                f"Ambiguous locator{count_info}.{locator_info} "
                f"Playwright suggests: `{suggestion_m.group(1)}`. "
                f"Use .filter({{ hasText: /pattern/ }}) or scope to the nearest unique parent container."
            )
        return (
            f"Ambiguous locator{count_info}.{locator_info} "
            f"Narrow it: add .filter({{ hasText: /expected_text/ }}) or scope to the nearest unique parent container."
        )

    # ── UNKNOWN / fallback ────────────────────────────────────────────────────
    return _fallback(error_type)


# Error classification patterns → targeted fix hints for Claude
_ERROR_PATTERNS: list[tuple[str, re.Pattern, str]] = [
    (
        "COMPILE_ERROR",
        re.compile(r"SyntaxError|error TS\d+|Cannot find|Module not found|Object\.<anonymous>|No tests found"),
        "TypeScript compile error — the tests never ran. Fix: import paths, missing exports, wrong class/property names. Do NOT change test logic.",
    ),
    (
        "LOCATOR_TIMEOUT",
        re.compile(r"TimeoutError.*locator|locator.*timeout|waiting for locator", re.IGNORECASE),
        "Locator timed out — element not found within timeout. Check: wrong role or name, element inside iframe, needs scroll into view, or Cloudflare blocked the page and replaced content.",
    ),
    (
        "ASSERTION_MISMATCH",
        re.compile(r"expect\(.*\)\.(toHaveText|toContainText|toBeVisible|toHaveURL|toHaveValue).*failed", re.IGNORECASE),
        "Assertion value mismatch. Check: use toContainText instead of toHaveText for partial match, add { exact: true } to getByText(), trim surrounding whitespace, verify the locator is scoped to the right element.",
    ),
    (
        "NAVIGATION_TIMEOUT",
        re.compile(r"page\.goto.*timeout|Navigation timeout|net::ERR_|ERR_CONNECTION", re.IGNORECASE),
        "Navigation timed out or network error. Check: BASE_URL is correct, site is reachable, Cloudflare is not serving a bot-challenge page to headless browser.",
    ),
    (
        "NETWORK_ERROR",
        re.compile(r"net::ERR_|ERR_CONNECTION|fetch failed|ECONNREFUSED", re.IGNORECASE),
        "Network error. Check: BASE_URL environment variable is set correctly, the site is reachable from this environment.",
    ),
    (
        "AMBIGUOUS_LOCATOR",
        re.compile(r"strict mode violation|resolved to \d+ elements|locator\(\) resolved to", re.IGNORECASE),
        "Ambiguous locator — matches multiple elements. Fix: narrow the selector using .filter({ hasText }), scope to a parent container, or use a more specific attribute selector.",
    ),
]


def _run_playwright(spec_rel: str) -> tuple[bool, str]:
    """Run a single spec file relative to playwright-framework/tests. Returns (passed, output)."""
    result = subprocess.run(
        f'npx playwright test "{spec_rel}" --reporter=list --timeout=30000',
        cwd=PLAYWRIGHT_DIR,
        capture_output=True, text=True, encoding="utf-8", timeout=120,
        shell=True,
    )
    return result.returncode == 0, (result.stdout + result.stderr)


def _summarise_output(output: str) -> str:
    """Extract a short human-readable summary from playwright list reporter output."""
    import re
    lines = output.splitlines()

    summary_line = ""
    for line in reversed(lines):
        stripped = line.strip()
        if re.search(r"\d+\s+(passed|failed)", stripped, re.IGNORECASE):
            summary_line = stripped
            break

    # Collect error blocks (● header + following lines until next blank/●)
    error_lines = []
    in_block = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("●"):
            in_block = True
            error_lines.append(stripped)
        elif in_block:
            if stripped == "" and len(error_lines) > 6:
                in_block = False
            else:
                error_lines.append(stripped)
        if len(error_lines) >= 20:
            break

    parts = []
    if summary_line:
        parts.append(f"`{summary_line}`")
    if error_lines:
        parts.append("```\n" + "\n".join(error_lines) + "\n```")
    return "\n".join(parts) if parts else "`(no summary available)`"


def _parse_failed_tests(output: str) -> list[str]:
    """Return list of failed TC names from playwright output."""
    import re
    failed = []
    for line in output.splitlines():
        # "x  3 [chromium] › tests/... › TC-05: ..."
        m = re.search(r"›\s+(TC-\d+[^()\n]*)", line)
        if m and ("x " in line or "failed" in line.lower()):
            failed.append(m.group(1).strip())
    return failed


def _parse_passing_tests(output: str) -> list[str]:
    """Return list of passing TC names from playwright output."""
    import re
    passing = []
    for line in output.splitlines():
        m = re.search(r"›\s+(TC-\d+[^()\n]*)", line)
        if m and "ok " in line:
            passing.append(m.group(1).strip())
    return passing


def _is_compile_error(output: str) -> bool:
    return any(hint in output for hint in COMPILE_ERROR_HINTS)


def _classify_error(output: str) -> tuple[str, str]:
    """Return (error_type, targeted_hint) based on failure output."""
    for error_type, pattern, hint in _ERROR_PATTERNS:
        if pattern.search(output):
            return error_type, hint
    return "UNKNOWN", "Read the full failure output carefully and fix the root cause."


def _run_tsc() -> tuple[bool, str]:
    """Run TypeScript compile check. Returns (clean, output). Faster feedback than playwright for compile errors."""
    result = subprocess.run(
        "npx tsc --noEmit",
        cwd=PLAYWRIGHT_DIR,
        capture_output=True, text=True, encoding="utf-8", timeout=60,
        shell=True,
    )
    return result.returncode == 0, (result.stdout + result.stderr).strip()


def _relevant_files(files: dict[str, str], error_output: str) -> dict[str, str]:
    """Return only files relevant to the error — spec always included, page objects only if mentioned."""
    relevant = {}
    for path, content in files.items():
        if path.endswith(".spec.ts"):
            relevant[path] = content
            continue
        stem = Path(path).stem
        filename = Path(path).name
        if stem in error_output or filename in error_output:
            relevant[path] = content
    return relevant if relevant else files


def _detect_flaky(pass_history: list[list[str]], fail_history: list[list[str]]) -> list[str]:
    """Return TC names that flipped between pass and fail across attempts — likely flaky, not broken."""
    all_tcs: set[str] = set()
    for lst in pass_history + fail_history:
        all_tcs.update(lst)
    return [
        tc for tc in all_tcs
        if any(tc in p for p in pass_history) and any(tc in f for f in fail_history)
    ]


def _parse_files(claude_output: str) -> dict[str, str]:
    files: dict[str, str] = {}
    sections = claude_output.split("=== FILE:")
    for section in sections[1:]:
        lines = section.strip().splitlines()
        file_path = lines[0].strip().rstrip("===").strip().strip("`")
        content_lines = lines[1:]
        while content_lines and content_lines[0].strip() == "":
            content_lines = content_lines[1:]
        if content_lines and content_lines[0].strip().startswith("```"):
            content_lines = content_lines[1:]
        while content_lines and content_lines[-1].strip() in ("```", "---", ""):
            content_lines = content_lines[:-1]
        if file_path and content_lines:
            files[file_path] = "\n".join(content_lines)
    return files


def _fix_with_claude(
    files: dict[str, str],
    error_output: str,
    ticket_id: str,
    passing_tests: list[str],
    attempt_history: list[str],
    error_type: str = "UNKNOWN",
    error_hint: str = "",
    flaky_tests: list[str] | None = None,
    strategy: str = "",
) -> dict[str, str] | None:
    """Ask Claude to fix failing scripts. Returns updated files or None."""
    # Only send files relevant to the error to reduce noise
    send_files = _relevant_files(files, error_output)

    file_block = "\n\n".join(
        f"=== FILE: {path} ===\n{content}"
        for path, content in send_files.items()
    )
    output_instructions = "\n\n".join(
        f"=== FILE: {path} ===\n<fixed content here>"
        for path in send_files
    )

    passing_note = ""
    if passing_tests:
        passing_note = (
            "\n## ✅ These tests are currently PASSING — do NOT touch their logic:\n"
            + "\n".join(f"- {t}" for t in passing_tests)
            + "\n"
        )

    flaky_note = ""
    if flaky_tests:
        flaky_note = (
            "\n## ⚠️  These tests are FLAKY (passed in some attempts, failed in others) — add `test.slow()` and a comment, do NOT change their locators:\n"
            + "\n".join(f"- {t}" for t in flaky_tests)
            + "\n"
        )

    history_note = ""
    if attempt_history:
        history_note = (
            "\n## Previous fix attempts (do not repeat the same fix):\n"
            + "\n".join(f"- Attempt {i+1}: {h}" for i, h in enumerate(attempt_history))
            + "\n"
        )

    # Use the LAST 4000 chars — Playwright errors are at the end of output
    error_tail = error_output[-4000:] if len(error_output) > 4000 else error_output

    strategy_note = f"\n## ✅ Strategy for this attempt\n{strategy}\nApply ONLY this strategy. Do not mix with other approaches.\n" if strategy else ""

    prompt = f"""You are fixing a failing Playwright TypeScript test script.

## Error Type: {error_type}
{error_hint}
{strategy_note}
## Rules
- Fix ONLY the failing tests — do not modify passing tests or refactor unrelated code.
- Do NOT remove or rename any imports, Page Object properties, or methods unless they are the direct cause of the error.
- Do NOT add new Page Object properties unless absolutely required by the fix.
- Output ONLY the fixed files using the delimiters below — no explanations.
{passing_note}{flaky_note}{history_note}
## Ticket: {ticket_id}

## Current File Contents (only files relevant to the failure)
{file_block}

## Failure Output (last 4000 chars — errors are here)
{error_tail}

## Output Format (reproduce ALL files sent above — no other text outside these delimiters)
{output_instructions}
"""
    output = call_claude(prompt, max_tokens=8096)
    if not output:
        return None
    fixed = _parse_files(output)
    return fixed if fixed else None


def _write_files_locally(files: dict[str, str]) -> None:
    for rel_path, content in files.items():
        local_path = Path(PROJECT_DIR) / rel_path
        local_path.parent.mkdir(parents=True, exist_ok=True)
        local_path.write_text(content, encoding="utf-8")


def build_test_healer_node():
    def test_healer(state: WorkflowState) -> WorkflowState:
        file_contents: dict = state.get("automation_file_contents", {})
        github_prs: dict = state.get("github_prs", {})
        channel = state.get("slack_channel")
        thread_ts = state.get("slack_thread_ts")

        print(f"[test_healer] file_contents keys: {list(file_contents.keys())}")

        if not file_contents:
            print("[test_healer] no file_contents in state — skipping.")
            return state

        healed_scripts: dict = {}

        for ticket_id, files in file_contents.items():
            print(f"[test_healer] {ticket_id}: files in state: {list(files.keys()) if files else 'empty'}")
            if not files:
                continue

            spec_files = [p for p in files if "tests/e2e/" in p and p.endswith(".spec.ts")]
            print(f"[test_healer] {ticket_id}: spec_files found: {spec_files}")
            if not spec_files:
                continue

            # Path relative to playwright-framework/ for npx playwright test
            spec_rel = spec_files[0].replace("playwright-framework/", "")

            if channel:
                notify_progress(channel,
                    f":stethoscope: *Self-Healer* — `{ticket_id}` | running scripts (max {MAX_ATTEMPTS} fix attempt(s))",
                    thread_ts)

            _write_files_locally(files)
            current_files = dict(files)
            final_status = "unknown"
            healed = False
            best_passing_count = 0
            best_files = dict(files)
            best_improved = False
            attempt_history: list[str] = []
            pass_history: list[list[str]] = []
            fail_history: list[list[str]] = []
            flaky_tests: list[str] = []

            for attempt in range(MAX_ATTEMPTS + 1):
                print(f"[test_healer] {ticket_id}: attempt {attempt + 1}/{MAX_ATTEMPTS + 1}")
                if channel:
                    notify_progress(channel,
                        f":arrow_forward: *Run {attempt + 1}/{MAX_ATTEMPTS + 1}* — `{ticket_id}` | executing `{spec_rel}`...",
                        thread_ts)

                # Fast compile check before running Playwright (saves time on TS errors)
                tsc_ok, tsc_out = _run_tsc()
                is_compile = not tsc_ok
                if is_compile:
                    print(f"[test_healer] {ticket_id}: tsc check FAILED:\n{tsc_out[:400]}")

                passed, output = _run_playwright(spec_rel)
                summary = _summarise_output(output)
                passing_tests = _parse_passing_tests(output)
                failed_tests = _parse_failed_tests(output)
                is_compile = is_compile or _is_compile_error(output)
                error_type, error_hint = _classify_error(output)

                pass_history.append(passing_tests)
                fail_history.append(failed_tests)
                flaky_tests = _detect_flaky(pass_history, fail_history)

                print(f"[test_healer] {ticket_id}: passing={passing_tests} failed={failed_tests} flaky={flaky_tests} error_type={error_type}")

                # Track best result to revert if a fix causes regression
                if len(passing_tests) > best_passing_count:
                    best_passing_count = len(passing_tests)
                    best_files = dict(current_files)
                    best_improved = True

                if passed:
                    final_status = "passed"
                    healed = attempt > 0
                    label = ":adhesive_bandage: healed and passing" if healed else "passing on first run"
                    print(f"[test_healer] {ticket_id}: PASSED on attempt {attempt + 1}")
                    if channel:
                        notify_progress(channel,
                            f":white_check_mark: *Self-Healer PASSED* — `{ticket_id}` | {label}\n{summary}",
                            thread_ts)
                    break

                print(f"[test_healer] {ticket_id}: FAILED on attempt {attempt + 1} [{error_type}]")
                print(f"[test_healer] {ticket_id}: playwright output (last 800 chars):\n{output[-800:]}")

                if attempt >= MAX_ATTEMPTS:
                    final_status = "failed"
                    # Revert to best seen version if current is worse
                    if best_improved and len(passing_tests) < best_passing_count:
                        print(f"[test_healer] {ticket_id}: reverting to best version ({best_passing_count} passing).")
                        _write_files_locally(best_files)
                        current_files = best_files
                    print(f"[test_healer] {ticket_id}: max attempts ({MAX_ATTEMPTS}) reached.")
                    if channel:
                        notify_progress(channel,
                            f":x: *Self-Healer FAILED* — `{ticket_id}` | gave up after {MAX_ATTEMPTS + 1} attempt(s)\n{summary}\n_PR left for manual review._",
                            thread_ts)
                    break

                if channel:
                    notify_progress(channel,
                        f":wrench: *Healing attempt {attempt + 1}/{MAX_ATTEMPTS}* — `{ticket_id}` | [{error_type}] asking Claude to fix\n{summary}",
                        thread_ts)

                print(f"[test_healer] {ticket_id}: calling Claude to fix (attempt {attempt + 1}/{MAX_ATTEMPTS}) [{error_type}] ...")
                strategy = _select_strategy(error_type, output, current_files, attempt)
                attempt_summary = f"{len(passing_tests)} passing, {len(failed_tests)} failing — {error_type}: {', '.join(failed_tests[:3])} | strategy: {strategy[:60]}..."
                attempt_history.append(attempt_summary)
                print(f"[test_healer] {ticket_id}: strategy → {strategy}")
                fixed = _fix_with_claude(
                    current_files, output, ticket_id,
                    passing_tests=passing_tests,
                    attempt_history=attempt_history,
                    error_type=error_type,
                    error_hint=error_hint,
                    flaky_tests=flaky_tests if flaky_tests else None,
                    strategy=strategy,
                )

                if not fixed:
                    print(f"[test_healer] {ticket_id}: Claude returned no fix on attempt {attempt + 1}.")
                    if channel:
                        notify_progress(channel,
                            f":warning: `{ticket_id}` | Claude returned no fix on attempt {attempt + 1}, retrying run as-is...",
                            thread_ts)
                    continue

                print(f"[test_healer] {ticket_id}: Claude patched {len(fixed)} file(s) — writing locally ...")
                _write_files_locally(fixed)
                current_files = {**current_files, **fixed}  # merge: keep files Claude didn't touch
                if channel:
                    notify_progress(channel,
                        f":memo: `{ticket_id}` | scripts patched by Claude — running again...",
                        thread_ts)

            # Push final (healed) scripts to GitHub and open PR
            pr_info = github_prs.get(ticket_id, {})
            branch_name = pr_info.get("branch")
            ticket_summary = pr_info.get("summary", ticket_id)
            source_label = pr_info.get("source_label", "generated")
            heal_label = "self-healed" if healed else "generated"

            import sys as _sys
            print(f"[test_healer] {ticket_id}: github_prs keys={list(github_prs.keys())} branch_name={branch_name!r}", file=_sys.stderr, flush=True)

            if not branch_name:
                print(f"[test_healer] {ticket_id}: WARNING — branch_name is empty, skipping GitHub push.", file=_sys.stderr, flush=True)
                if channel:
                    notify_progress(channel, f":warning: `{ticket_id}` — no branch name found, PR skipped. Check automator output.", thread_ts)

            if branch_name:
                try:
                    print(f"[test_healer] {ticket_id}: creating branch {branch_name} ...", file=_sys.stderr, flush=True)
                    create_branch(branch_name, from_branch=GITHUB_DEFAULT_BRANCH)

                    print(f"[test_healer] {ticket_id}: committing {len(current_files)} file(s): {list(current_files.keys())}", file=_sys.stderr, flush=True)
                    commit_files(
                        branch_name=branch_name,
                        files=current_files,
                        message=f"feat(qa-bot): {heal_label} automation scripts for {ticket_id} — {final_status}",
                    )

                    flaky_section = ""
                    if flaky_tests:
                        flaky_section = (
                            "\n### ⚠️ Suspected Flaky Tests\n"
                            + "\n".join(f"- {t}" for t in flaky_tests)
                            + "\n_These passed in some attempts and failed in others — marked with `test.slow()`, review manually._\n"
                        )
                    pr_body = (
                        f"## Auto-generated by Quality-Engineer-Bot\n\n"
                        f"**Ticket:** {ticket_id} — {ticket_summary}\n"
                        f"**Source:** {source_label}\n"
                        f"**Self-Healing:** {heal_label} | local run status: `{final_status}`\n"
                        f"{flaky_section}\n"
                        f"### Files\n"
                        + "\n".join(f"- `{p}`" for p in current_files)
                        + "\n\n> Do **not** merge manually — this PR is managed by QA Bot."
                    )
                    pr = create_pull_request(
                        branch_name=branch_name,
                        base_branch=GITHUB_DEFAULT_BRANCH,
                        title=f"[QA Bot] {ticket_id} — {ticket_summary}",
                        body=pr_body,
                    )
                    github_prs[ticket_id] = {**pr_info, "pr_url": pr["url"], "pr_number": pr["number"]}
                    print(f"[test_healer] {ticket_id}: PR #{pr['number']} opened: {pr['url']}", file=_sys.stderr, flush=True)
                    if channel:
                        notify_progress(channel,
                            f":github: PR #{pr['number']} created for `{ticket_id}` ({heal_label}): {pr['url']}\nBranch: `{branch_name}`",
                            thread_ts)
                except Exception as exc:
                    print(f"[test_healer] {ticket_id}: GitHub push failed: {exc}", file=_sys.stderr, flush=True)
                    if channel:
                        notify_progress(channel, f":warning: `{ticket_id}` — GitHub push failed: {exc}", thread_ts)

            healed_scripts[ticket_id] = {
                "status": final_status,
                "healed": healed,
                "files": list(current_files.keys()),
            }

        return {**state, "healed_scripts": healed_scripts, "github_prs": github_prs}

    return test_healer
