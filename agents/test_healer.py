"""
Node 4 — Self-Healing Agent
Runs generated Playwright scripts locally, detects failures,
and calls Claude Code CLI to fix them — up to MAX_ATTEMPTS retries.
Pushes the final (healed or not) files back to the same GitHub branch.
"""
import subprocess
from pathlib import Path
from state import WorkflowState
from tools.slack_client import notify_progress
from tools.github_client import create_branch, commit_files, create_pull_request
from config import PROJECT_DIR, CLAUDE_CMD, GITHUB_DEFAULT_BRANCH

MAX_ATTEMPTS = 2
PLAYWRIGHT_DIR = str(Path(PROJECT_DIR) / "playwright-framework")


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

    # Look for the summary line: e.g. "3 passed (12s)" or "2 failed, 1 passed"
    summary_line = ""
    for line in reversed(lines):
        stripped = line.strip()
        if re.search(r"\d+\s+(passed|failed)", stripped, re.IGNORECASE):
            summary_line = stripped
            break

    # Collect first error message (lines starting with "●" or "Error:")
    error_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith(("Error:", "●", "expect(")):
            error_lines.append(stripped)
        if len(error_lines) >= 3:
            break

    parts = []
    if summary_line:
        parts.append(f"`{summary_line}`")
    if error_lines:
        parts.append("```\n" + "\n".join(error_lines[:3]) + "\n```")
    return "\n".join(parts) if parts else "`(no summary available)`"


def _parse_files(claude_output: str) -> dict[str, str]:
    files: dict[str, str] = {}
    sections = claude_output.split("=== FILE:")
    for section in sections[1:]:
        lines = section.strip().splitlines()
        file_path = lines[0].strip().rstrip("===").strip()
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


def _fix_with_claude(files: dict[str, str], error_output: str, ticket_id: str) -> dict[str, str] | None:
    """Ask Claude to fix failing scripts. Returns updated files or None."""
    file_block = "\n\n".join(
        f"=== FILE: {path} ===\n{content}"
        for path, content in files.items()
    )
    output_instructions = "\n\n".join(
        f"=== FILE: {path} ===\n<fixed content here>"
        for path in files
    )
    prompt = f"""You are fixing a failing Playwright TypeScript test script.

## Rules
- Fix ONLY what is broken — do not refactor, rename, or add new tests.
- Common issues: wrong locators, missing awaits, bad import paths, type errors.
- Output ONLY the fixed files using the delimiters below — no explanations.

## Ticket: {ticket_id}

## Current File Contents
{file_block}

## Failure Output
{error_output[:4000]}

## Output Format (no other text outside these delimiters)
{output_instructions}
"""
    result = subprocess.run(
        [CLAUDE_CMD, "--print", "--output-format", "text"],
        input=prompt,
        capture_output=True, text=True, encoding="utf-8",
        timeout=300, cwd=PROJECT_DIR,
    )
    output = result.stdout.strip()
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

        if not file_contents:
            return state

        healed_scripts: dict = {}

        for ticket_id, files in file_contents.items():
            if not files:
                continue

            spec_files = [p for p in files if "tests/e2e/" in p and p.endswith(".spec.ts")]
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

            for attempt in range(MAX_ATTEMPTS + 1):
                print(f"[test_healer] {ticket_id}: attempt {attempt + 1}/{MAX_ATTEMPTS + 1}")
                if channel:
                    notify_progress(channel,
                        f":arrow_forward: *Run {attempt + 1}/{MAX_ATTEMPTS + 1}* — `{ticket_id}` | executing `{spec_rel}`...",
                        thread_ts)

                passed, output = _run_playwright(spec_rel)
                summary = _summarise_output(output)

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

                print(f"[test_healer] {ticket_id}: FAILED on attempt {attempt + 1}")

                if attempt >= MAX_ATTEMPTS:
                    final_status = "failed"
                    print(f"[test_healer] {ticket_id}: max attempts ({MAX_ATTEMPTS}) reached.")
                    if channel:
                        notify_progress(channel,
                            f":x: *Self-Healer FAILED* — `{ticket_id}` | gave up after {MAX_ATTEMPTS + 1} attempt(s)\n{summary}\n_PR left for manual review._",
                            thread_ts)
                    break

                if channel:
                    notify_progress(channel,
                        f":wrench: *Healing attempt {attempt + 1}/{MAX_ATTEMPTS}* — `{ticket_id}` | asking Claude to fix\n{summary}",
                        thread_ts)

                fixed = _fix_with_claude(current_files, output, ticket_id)
                if not fixed:
                    print(f"[test_healer] {ticket_id}: Claude returned no fix on attempt {attempt + 1}.")
                    if channel:
                        notify_progress(channel,
                            f":warning: `{ticket_id}` | Claude returned no fix on attempt {attempt + 1}, retrying run as-is...",
                            thread_ts)
                    continue

                _write_files_locally(fixed)
                current_files = fixed
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

            if branch_name:
                try:
                    print(f"[test_healer] {ticket_id}: creating branch {branch_name} ...")
                    create_branch(branch_name, from_branch=GITHUB_DEFAULT_BRANCH)

                    print(f"[test_healer] {ticket_id}: committing {len(current_files)} file(s) ...")
                    commit_files(
                        branch_name=branch_name,
                        files=current_files,
                        message=f"feat(qa-bot): {heal_label} automation scripts for {ticket_id} — {final_status}",
                    )

                    pr_body = (
                        f"## Auto-generated by Quality-Engineer-Bot\n\n"
                        f"**Ticket:** {ticket_id} — {ticket_summary}\n"
                        f"**Source:** {source_label}\n"
                        f"**Self-Healing:** {heal_label} | local run status: `{final_status}`\n\n"
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
                    print(f"[test_healer] {ticket_id}: PR #{pr['number']} opened: {pr['url']}")
                    if channel:
                        notify_progress(channel,
                            f":github: PR #{pr['number']} created for `{ticket_id}` ({heal_label}): {pr['url']}\nBranch: `{branch_name}`",
                            thread_ts)
                except Exception as exc:
                    print(f"[test_healer] {ticket_id}: GitHub push failed: {exc}")
                    if channel:
                        notify_progress(channel, f":warning: `{ticket_id}` — GitHub push failed: {exc}", thread_ts)

            healed_scripts[ticket_id] = {
                "status": final_status,
                "healed": healed,
                "files": list(current_files.keys()),
            }

        return {**state, "healed_scripts": healed_scripts}

    return test_healer
