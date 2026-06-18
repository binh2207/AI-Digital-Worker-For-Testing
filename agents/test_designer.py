"""
Node 1 — Test Designer Agent
Calls Claude Code CLI to extract acceptance criteria from the JIRA ticket
and generate exactly one test case per criterion — no extras.
"""
from state import WorkflowState
from tools.jira_client import add_comment
from tools.slack_client import notify_progress
from tools.claude_client import call_claude
from config import PLAYWRIGHT_BASE_URL


def build_test_designer_node():
    def test_designer(state: WorkflowState) -> WorkflowState:
        tickets = state.get("jira_tickets", [])
        channel = state.get("slack_channel")
        thread_ts = state.get("slack_thread_ts")
        if not tickets:
            return {**state, "error": "No tickets found in Review column."}

        test_cases: dict = {}

        for ticket in tickets:
            ticket_id = ticket["id"]
            description = ticket["description"] or ""

            if channel:
                notify_progress(channel, f":pencil: Designing test cases for `{ticket_id}`: _{ticket['summary']}_", thread_ts)

            prompt = f"""You are a senior QA engineer writing test cases for a JIRA ticket.

## Your Rules (follow strictly)

1. Read the Acceptance Criteria (AC) from the ticket description below.
2. Write EXACTLY ONE test case per acceptance criterion — no more, no less.
3. Do NOT add test cases for things not mentioned in the AC (no "happy path extras", no negative cases unless the AC explicitly states them, no edge cases you invented).
4. If an AC item is not testable via UI (e.g. a backend rule), mark it: **[NON-UI — skip]**
5. Title each test case by quoting or paraphrasing the AC item it covers.
6. Steps must be concrete UI actions a human (or browser agent) can perform on {PLAYWRIGHT_BASE_URL}.

## Ticket

**ID:** {ticket_id}
**Summary:** {ticket["summary"]}

**Description / SRS:**
{description or "(no description provided)"}

## Output format (output ONLY this — no preamble, no commentary)

# Test Cases — {ticket_id}: {ticket["summary"]}
> Mapped from {{}}_n_{{}} acceptance criteria

## TC-01: <exact AC item paraphrased>
**AC Reference:** <quote the AC bullet verbatim>
**Preconditions:** <what must be true before the test, or "None">
**Steps:**
1. <concrete UI action>
2. <concrete UI action>
**Expected Result:** <observable outcome that proves the AC is met>

## TC-02: ...
"""

            print(f"[test_designer] Generating test cases for {ticket_id} ...")
            markdown = call_claude(prompt)
            if not markdown:
                print(f"[test_designer] {ticket_id}: no output from Claude API.")
                continue

            test_cases[ticket_id] = markdown
            print(f"[test_designer] {ticket_id}: {markdown.count('## TC-')} test case(s) generated.")

            jira_comment = (
                f"*[Quality-Engineer-Bot] Test Cases*\n\n"
                f"{{noformat}}\n{markdown}\n{{noformat}}"
            )
            try:
                add_comment(ticket_id, jira_comment)
                print(f"[test_designer] {ticket_id}: posted to JIRA.")
            except Exception as exc:
                print(f"[test_designer] Failed to comment on {ticket_id}: {exc}")

        return {**state, "test_cases": test_cases}

    return test_designer
