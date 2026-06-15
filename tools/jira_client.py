from jira import JIRA
from config import JIRA_URL, JIRA_USER, JIRA_API_TOKEN, JIRA_PROJECT_KEY, JIRA_REVIEW_COLUMN


def get_jira_client() -> JIRA:
    return JIRA(
        server=JIRA_URL,
        basic_auth=(JIRA_USER, JIRA_API_TOKEN),
    )


def get_review_tickets() -> list[dict]:
    """Fetch all tickets currently in the Review column."""
    jira = get_jira_client()
    jql = f'project = "{JIRA_PROJECT_KEY}" AND status = "{JIRA_REVIEW_COLUMN}" ORDER BY updated DESC'
    issues = jira.search_issues(jql, maxResults=50, fields="summary,description,status,assignee,priority")
    return [
        {
            "id": issue.key,
            "summary": issue.fields.summary,
            "description": issue.fields.description or "",
            "status": issue.fields.status.name,
            "assignee": getattr(issue.fields.assignee, "displayName", "Unassigned"),
            "assignee_email": getattr(issue.fields.assignee, "emailAddress", None),
            "priority": issue.fields.priority.name if issue.fields.priority else "Medium",
        }
        for issue in issues
    ]


def add_comment(ticket_id: str, body: str) -> None:
    jira = get_jira_client()
    jira.add_comment(ticket_id, body)


def get_test_cases_from_comment(ticket_id: str) -> str | None:
    """Return the Markdown test cases from the most recent Quality-Engineer-Bot comment."""
    jira = get_jira_client()
    comments = jira.comments(ticket_id)
    for comment in reversed(comments):
        body = comment.body or ""
        if "[Quality-Engineer-Bot] Test Cases" in body:
            start = body.find("{noformat}")
            end = body.find("{noformat}", start + len("{noformat}"))
            if start != -1 and end != -1:
                return body[start + len("{noformat}"):end].strip()
    return None


def transition_ticket(ticket_id: str, target_status: str) -> None:
    """Transition a ticket to the given status name if a matching transition exists."""
    jira = get_jira_client()
    transitions = jira.transitions(ticket_id)
    match = next((t for t in transitions if t["name"].lower() == target_status.lower()), None)
    if match:
        jira.transition_issue(ticket_id, match["id"])
